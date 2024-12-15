from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import time
from math import comb
from tqdm import tqdm

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///skills.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tags = db.Column(db.String(500), nullable=False)

    def get_tags(self):
        return set(tag.strip() for tag in self.tags.split(',') if tag.strip())

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_skill', methods=['POST'])
def add_skill():
    data = request.json
    name = data.get('name')
    tags = ','.join(data.get('tags', []))
    
    new_skill = Skill(name=name, tags=tags)
    db.session.add(new_skill)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/delete_skill/<int:skill_id>', methods=['DELETE'])
def delete_skill(skill_id):
    skill = Skill.query.get_or_404(skill_id)
    db.session.delete(skill)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/get_skills')
def get_skills():
    search_query = request.args.get('search', '').lower()
    filter_tags = request.args.getlist('tags[]')
    
    skills = Skill.query.all()
    filtered_skills = []
    
    for skill in skills:
        skill_tags = skill.get_tags()
        skill_name = skill.name.lower()
        
        # 如果有搜索词，检查名称和标签是否匹配
        if search_query:
            if search_query not in skill_name and \
               not any(search_query in tag.lower() for tag in skill_tags):
                continue
        
        # 如果有标签过滤，检查是否包含所有指定标签
        if filter_tags and not all(tag in skill_tags for tag in filter_tags):
            continue
            
        filtered_skills.append({
            'id': skill.id,
            'name': skill.name,
            'tags': list(skill_tags)
        })
    
    return jsonify(filtered_skills)

@app.route('/get_all_tags')
def get_all_tags():
    skills = Skill.query.all()
    all_tags = set()
    for skill in skills:
        all_tags.update(skill.get_tags())
    return jsonify(list(all_tags))

@app.route('/search_combinations', methods=['POST'])
def search_combinations():
    start_time = time.time()
    
    data = request.json
    required_tags = set(data.get('required_tags', []))
    tag_counts = data.get('tag_counts', {})
    max_skills = data.get('max_skills', 10)
    
    print(f"\n搜索条件: {required_tags=}, {tag_counts=}, {max_skills=}")
    
    # 1. 预处理
    all_skills = Skill.query.all()
    skill_tags = [(skill, skill.get_tags()) for skill in all_skills]
    
    # 过滤功法
    filtered_skills = []
    
    if required_tags or tag_counts:
        needed_tags = required_tags.union(tag_counts.keys())
        
        # 构建标签到功法的映射
        tag_to_skills = {tag: set() for tag in needed_tags}
        
        for skill, tags in skill_tags:
            for tag in tags:
                if tag in needed_tags:
                    tag_to_skills[tag].add(skill)
                    
        candidate_skills = set()
        for tag in needed_tags:
            candidate_skills.update(tag_to_skills[tag])
        
        for skill in candidate_skills:
            skill_tag_set = set(tag.strip() for tag in skill.tags.split(',') if tag.strip())
            filtered_skills.append((skill, skill_tag_set))
    else:
        filtered_skills = skill_tags

    print(f"过滤后功法数量: {len(filtered_skills)}")

    if not filtered_skills:
        return jsonify([])

    # 计算总组合数
    n = len(filtered_skills)
    total_combinations = comb(n, max_skills)
    print(f"需要检查的组合总数: {total_combinations}")

    valid_combinations = []
    
    # 创建进度条
    pbar = tqdm(total=total_combinations, desc="搜索组合", unit="combo")

    def check_combination_valid(combo):
        pbar.update(1)  # 更新进度条
        
        tag_counts_map = {}
        for skill, tags in combo:
            for tag in tags:
                tag_counts_map[tag] = tag_counts_map.get(tag, 0) + 1
        
        # 快速检查标签数量要求
        if not all(tag_counts_map.get(tag, 0) >= count for tag, count in tag_counts.items()):
            return False
            
        # 检查必需标签
        if required_tags and not all(tag in tag_counts_map for tag in required_tags):
            return False
        
        valid_combinations.append({
            'skills': [{'name': skill.name, 'tags': list(tags)} for skill, tags in combo],
            'combined_tags': tag_counts_map
        })
        
        # 更新进度条描述以显示找到的有效组合数
        pbar.set_postfix({'找到': len(valid_combinations)})
        return True

    current_combo = []
    def find_combinations(start_idx, remaining):
        if len(valid_combinations) >= 1000:
            return
            
        if remaining == 0:
            check_combination_valid(current_combo)
            return
        
        if len(filtered_skills) - start_idx < remaining:
            # 更新跳过的组合数
            skipped = comb(len(filtered_skills) - start_idx, remaining)
            pbar.update(skipped)
            return
        
        for i in range(start_idx, len(filtered_skills)):
            current_combo.append(filtered_skills[i])
            find_combinations(i + 1, remaining - 1)
            current_combo.pop()

    try:
        find_combinations(0, max_skills)
    finally:
        pbar.close()  # 确保进度条正常关闭

    end_time = time.time()
    print(f"\n搜索完成: 找到 {len(valid_combinations)} 个有效组合")
    print(f"总耗时: {end_time - start_time:.1f}s")
    
    return jsonify(valid_combinations)

if __name__ == '__main__':
    app.run(debug=True)