from flask import Flask, render_template, request
from langchain.chat_models import ChatOpenAI
from langchain.chains import GraphCypherQAChain
from langchain.graphs import Neo4jGraph
from dotenv import load_dotenv
import os
import neo4j
import io
import sys
import re

graph = Neo4jGraph(
    url="neo4j+s://38951e74.databases.neo4j.io", 
    username="neo4j", 
    password="kU3RG9BdAP5lCpqCsLyuLx_0ICL6L8y2WHj6LmdextU"
)

load_dotenv()

app = Flask(__name__)

neo4j_url = os.getenv('NEO4J_URL')
neo4j_user = os.getenv('NEO4J_USER')
neo4j_password = os.getenv('NEO4J_PASSWORD')

chain = GraphCypherQAChain.from_llm(
    ChatOpenAI(temperature=0), graph=graph, verbose=True,
)

@app.route('/')
def home():
    return render_template('index.html')


@app.route('/get', methods=['POST'])
def get_bot_response():
    question = request.form.get('msg')
    
    old_stdout = sys.stdout
    captured_output = io.StringIO()
    sys.stdout = captured_output

    response = chain.run(question)

    sys.stdout = old_stdout
    output = captured_output.getvalue()
    output = output.replace('\n', '<br>')
    # This pattern matches ANSI escape codes
    ansi_escape_pattern = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')

    # This replaces ANSI escape codes with an empty string
    clean_output = ansi_escape_pattern.sub('', output)

    return response + "<br>" + "<br>" + "The log of chain process is: "  + clean_output

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000, debug=True)
