from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import redis
import os
import json

app = Flask(__name__)
CORS(app)

# Configurare PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'postgresql://taskuser:taskpass@postgresql:5432/taskdb'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configurare Redis
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=6379,
    decode_responses=True
)

# Model Task
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500))
    done = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'done': self.done
        }

# Routes
@app.route('/health')
def health():
    return jsonify({"status": "healthy"})

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    cached = redis_client.get('tasks')
    if cached:
        return jsonify(json.loads(cached))
    tasks = Task.query.all()
    result = [t.to_dict() for t in tasks]
    redis_client.setex('tasks', 60, json.dumps(result))
    return jsonify(result)

@app.route('/api/tasks', methods=['POST'])
def create_task():
    data = request.get_json()
    task = Task(
        title=data['title'],
        description=data.get('description', '')
    )
    db.session.add(task)
    db.session.commit()
    redis_client.delete('tasks')
    return jsonify(task.to_dict()), 201

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json()
    task.done = data.get('done', task.done)
    task.title = data.get('title', task.title)
    db.session.commit()
    redis_client.delete('tasks')
    return jsonify(task.to_dict())

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    redis_client.delete('tasks')
    return jsonify({"message": "deleted"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)
