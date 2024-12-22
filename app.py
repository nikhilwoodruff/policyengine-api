import streamlit as st
import openai
import json
import requests
from policyengine_uk import Simulation

def print_inputs_outputs(fn):
    return fn
    def wrapper(*args, **kwargs):
        st.write(f"{fn.__name__} inputs: {args}, {kwargs}")
        result = fn(*args, **kwargs)
        st.write(f"{fn.__name__} outputs: {result}")
        return result
    return wrapper


class GPTAgent:
    gpt_model = "gpt-4"

    capabilities_description: str = ""

    def process(self, text: str) -> str:
        raise NotImplementedError("Must implement process method")
    
    def __str__(self):
        return self.__class__.__name__
    
    def _get_chatgpt_response(self, text: str) -> str:
        response = openai.ChatCompletion.create(
            model=self.gpt_model,
            messages=[{
                "role": "user",
                "content": text
            }]
        )
        return response.choices[0].message.content


metadata = requests.get("https://api.policyengine.org/uk/metadata").json()["result"]

class InputHouseholdConstructor(GPTAgent):
    gpt_model = "gpt-3.5-turbo"

    capabilities_description = "Constructs a household object given a description"

    @print_inputs_outputs
    def process(self, text: str) -> str:
        example_household = {
            "people": {
                "person_1": {
                    "age": {"2023": 30},
                    "employment_income": {"2023": 30000},
                },
            },
            "households": {
                "household": {
                    "members": ["person_1"],
                },
            },
        }
        PROMPT = f"""You need to construct a PolicyEngine-compatible household JSON object from the user's description. Here's a valid example:
        {example_household}
        Description: {text}
        Remember JSON must use double quotes etc.
        JSON result:
        """
        return self._get_chatgpt_response(PROMPT)

class VariableCalculator(GPTAgent):
    gpt_model = None

    capabilities_description = "Calculates net income given a (stringified) JSON object {{household: <household object>, variable_name: <variable_name>}}"

    @print_inputs_outputs
    def process(self, text: str) -> str:
        input_data = json.loads(text)
        sim = Simulation(situation=input_data["household"])
        return str(sim.calculate(input_data["variable_name"]).sum())
    
class NormalGPTAgent(GPTAgent):
    gpt_model = "gpt-3.5-turbo"
    capabilities_description = "Just sends the text to GPT-4 and returns the response."

    @print_inputs_outputs
    def process(self, text: str) -> str:
        return self._get_chatgpt_response(text + "do not cop out: all the data you need is given.")
    
agents = [NormalGPTAgent(), InputHouseholdConstructor(), VariableCalculator()]

class GPTAgentManager(GPTAgent):
    gpt_model = "gpt-4"
    capabilities_description = "Receives a question and formulates a Python script that can answer it, given information about the capabilities of GPT-powered agents it can interact with."

    def process(self, text: str) -> dict:
        PROMPT = f"""
            Task: answer the following question with a Python code snippet that can be run to answer the question.
            You have several Python GPTAgent classes you can use. Each GPTAgent has the method process(text) that takes a string and returns a string. Each GPTAgent also has a capabilities_description attribute that describes what it can do. Here is a list of GPTAgents you can use:
            {[dict(name=agent.__class__.__name__, description=agent.capabilities_description) for agent in agents]}
            You need to write a Python script, specifying which GPTAgent to use and what text (or the output of which agent) to pass to the process method. 
            All agents receive and return strings.
            Here is an example:
            'what's my net income at 40k earnings?'
            answer:
            household = InputHouseholdConstructor().process("I am 30 years old and earn 40k")
            net_income = VariableCalculator().process(json.dumps(dict(household=json.loads(household), variable_name="net_income")))
            answer = NormalGPTAgent().process(f"summarise to the user that their net income is {{net_income}}, with appropriate formatting (don't cop out and give me rubbish)")
            
            Here is the user's question, respond with valid Python text that can be run through exec (must store the answer in a variable called answer):"""
        python_code = self._get_chatgpt_response(PROMPT + text)
        # st.write(f"```python\n{python_code}```")
        local_variables = {
            "InputHouseholdConstructor": InputHouseholdConstructor,
            "VariableCalculator": VariableCalculator,
            "NormalGPTAgent": NormalGPTAgent,
            "json": json,
        }
        exec(python_code, {}, local_variables)
        answer = local_variables["answer"]
        return answer

text = st.text_input("Enter text")
submit = st.button("Submit")
answer = None
if submit:
    answer_question = GPTAgentManager().process(text)
    st.write(answer_question)