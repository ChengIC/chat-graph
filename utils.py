from neo4j import GraphDatabase
from neo4j.exceptions import CypherSyntaxError
import openai

class MyObject:
    def __init__(self, name, description):
        self.name = name
        self.description = description

    def __str__(self):
        return f'Name: {self.name}, Description: {self.description}'
    
node_properties_query = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE NOT type = "RELATIONSHIP" AND elementType = "node"
WITH label AS nodeLabels, collect(property) AS properties
RETURN {labels: nodeLabels, properties: properties} AS output

"""

rel_properties_query = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE NOT type = "RELATIONSHIP" AND elementType = "relationship"
WITH label AS nodeLabels, collect(property) AS properties
RETURN {type: nodeLabels, properties: properties} AS output
"""

rel_query = """
CALL apoc.meta.data()
YIELD label, other, elementType, type, property
WHERE type = "RELATIONSHIP" AND elementType = "node"
RETURN {source: label, relationship: property, target: other} AS output
"""

def schema_text(node_props, rel_props, rels):
    return f"""
  This is the schema representation of the Neo4j database.
  Node properties are the following:
  {node_props}
  Relationship properties are the following:
  {rel_props}
  Relationship point from source to target nodes
  {rels}
  Make sure to respect relationship types and directions
  """


class Neo4jGPTQuery:
    def __init__(self, url, user, password, openai_api_key):
        self.driver = GraphDatabase.driver(url, auth=(user, password))
        openai.api_key = openai_api_key
        # construct schema
        self.schema = self.generate_schema()


    def generate_schema(self):
        node_props = self.query_database(node_properties_query)
        rel_props = self.query_database(rel_properties_query)
        rels = self.query_database(rel_query)
        return schema_text(node_props, rel_props, rels)

    def refresh_schema(self):
        self.schema = self.generate_schema()

    def get_system_message(self):
        return f"""
        Task: Generate Cypher queries to query a Neo4j graph database based on the provided schema definition.
        Instructions:
        Use only the provided relationship types and properties.
        Do not use any other relationship types or properties that are not provided.
        If you cannot generate a Cypher statement based on the provided schema, explain the reason to the user.
        Schema:
        {self.schema}

        Note: Do not include any explanations or apologies in your responses.
        """

    def query_database(self, neo4j_query, params={}):
        with self.driver.session() as session:
            result = session.run(neo4j_query, params)
            output = [r.values() for r in result]
            output.insert(0, result.keys())
            return output

    def construct_cypher(self, question, history=None):
        messages = [
            {"role": "system", "content": self.get_system_message()},
            {"role": "user", "content": question},
        ]
        # Used for Cypher healing flows
        if history:
            messages.extend(history)

        completions = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature=0.0,
            max_tokens=1000,
            messages=messages
        )
        return completions.choices[0].message.content

    def run(self, question, history=None, retry=True):
        cypher = self.construct_cypher(question, history)
        print (f"RETRY is {retry}",cypher)
        try:
            result = self.query_database(cypher)
            return result
        
        # Self-healing flow
        except CypherSyntaxError as e:
            # If out of retries
            if not retry:
                return f"Not successful qurying the database, {cypher}"
            # Self-healing Cypher flow by
            # providing specific error to GPT-4
            print("Retrying")
            return self.run(
                question,
                [
                    {"role": "assistant", "content": cypher},
                    {
                        "role": "user",
                        "content": f"""This query returns an error: {str(e)} 
                        Give me a improved query that works without any explanations or apologies""",
                    },
                ],
                retry=False
            )
        
        
if __name__ == '__main__':
    from dotenv import load_dotenv
    import os
    load_dotenv()

    # Now you can access your environment variables
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
    print (ps_db.run("What are the nodes in the databse?"))
    ps_db.driver.close()
