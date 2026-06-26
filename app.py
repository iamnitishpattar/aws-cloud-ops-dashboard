from flask import Flask, render_template, request, jsonify, redirect, url_for
from aws_deploy import deploy_instance
from aws_monitor import monitor_instance
from terminate import terminate_instance, terminate_all_project_instances
from manager import get_instances

app = Flask(__name__)

@app.route('/')
def index():
    # Fetch instances on page load
    try:
        instances = get_instances()
        active_instances = [i for i in instances if i['state'] not in ['terminated', 'shutting-down']]
        terminated_instances = [i for i in instances if i['state'] in ['terminated', 'shutting-down']]
        error = None
    except Exception as e:
        active_instances = []
        terminated_instances = []
        error = str(e)
    return render_template('index.html', active_instances=active_instances, terminated_instances=terminated_instances, error=error)

@app.route('/deploy', methods=['POST'])
def deploy():
    try:
        data = request.get_json() or {}
        template = data.get('template', 'nginx')
        instance_id = deploy_instance(template)
        return jsonify({"status": "success", "instance_id": instance_id})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/monitor/<instance_id>', methods=['GET'])
def monitor(instance_id):
    try:
        metrics = monitor_instance(instance_id)
        return jsonify({"status": "success", "metrics": metrics})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/terminate/<instance_id>', methods=['POST'])
def terminate(instance_id):
    try:
        if instance_id == 'all':
            terminate_all_project_instances()
        else:
            terminate_instance(instance_id)
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # Run the Flask server
    app.run(debug=True, port=5000)
