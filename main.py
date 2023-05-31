from flask import Flask, render_template, request
from neo4j import GraphDatabase
from neo4j.exceptions import CypherSyntaxError
import openai
import os
from dotenv import load_dotenv
from utils import Neo4jGPTQuery
import neo4j
load_dotenv()

app = Flask(__name__)

neo4j_url = os.getenv('NEO4J_URL')
neo4j_user = os.getenv('NEO4J_USER')
neo4j_password = os.getenv('NEO4J_PASSWORD')
openai_key = os.getenv('OPENAI_KEY')

ps_db = Neo4jGPTQuery(
    url=neo4j_url,
    user=neo4j_user,
    password=neo4j_password,
    openai_api_key=openai_key,
)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/get', methods=['POST'])
def get_bot_response():
    question = request.form.get('msg')
    response = ps_db.run(question)
    # Convert the Neo4j objects to a string representation
    if isinstance(response, list):
        response_str = []
        for item in response:
            record = item[0]
            if isinstance(record, neo4j.graph.Node):  # If the item is a Node
                response_str.append(str(dict(record)))
            elif isinstance(record, neo4j.graph.Relationship):  # If the item is a Relationship
                response_str.append(f"({dict(record.start_node)})-[:{record.type}]->({dict(record.end_node)})")
            else:
                response_str.append(str(record))

        return ', '.join(response_str)
    else:
        return response
    
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)
