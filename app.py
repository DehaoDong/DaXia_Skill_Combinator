from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from itertools import combinations

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
    data = request.json
    required_tags = set(data.get('required_tags', []))  # 需要的标签列表
    tag_counts = data.get('tag_counts', {})  # 每个标签需要的最小数量
    max_skills = data.get('max_skills', 5)
    
    all_skills = Skill.query.all()
    valid_combinations = []
    
    # 遍历所有可能的组合（从1个到max_skills个）
    for n in range(1, max_skills + 1):
        for combo in combinations(all_skills, n):
            # 计算组合中所有功法的标签
            combined_tags = {}
            for skill in combo:
                for tag in skill.get_tags():
                    combined_tags[tag] = combined_tags.get(tag, 0) + 1
            
            # 检查是否满足所有要求
            if not required_tags or all(tag in combined_tags for tag in required_tags):
                if all(combined_tags.get(tag, 0) >= count for tag, count in tag_counts.items()):
                    valid_combinations.append({
                        'skills': [{'name': skill.name, 'tags': list(skill.get_tags())} for skill in combo],
                        'combined_tags': combined_tags
                    })
    
    return jsonify(valid_combinations)

if __name__ == '__main__':
    app.run(debug=True)