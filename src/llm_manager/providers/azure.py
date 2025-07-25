from openai import AzureOpenAI
from .base import BaseProvider
import warnings

class AzureProvider(BaseProvider):
    """Provider for Azure OpenAI models"""
    
    def __init__(self, config):
        super().__init__(config)
        self.models = config.get("models", {})
        self.reasoning_effort_models = ["o1", "o3-mini", "o3", "o4-mini"]
        self.reasoning_summary_supported= ["o3", "o4-mini"]
    
    def generate(self, prompt, model_id, **kwargs):
        """Generate a response using the specified Azure model"""
        if not self.is_enabled():
            raise ValueError("Azure provider is not enabled")
        
        if model_id not in self.models:
            raise ValueError(f"Unknown Azure model: {model_id}")
        
        model_config = self.models[model_id]

        request_kwargs = kwargs.copy()

        if "system" in request_kwargs:
            system_prompt = request_kwargs.get("system", "")
            request_kwargs.pop("system")

        else:
            system_prompt = ""

        if "reasoning_effort" in request_kwargs:
            model_name = model_config.get("model_id", "").lower()
            supports_reasoning = any(model in model_name for model in self.reasoning_effort_models)
            supports_reasoning_summary = any(model in model_name for model in self.reasoning_summary_supported)
            
            if not supports_reasoning:
                request_kwargs.pop("reasoning_effort")

                compatible_models = ", ".join(self.reasoning_effort_models)
                warning_msg = (
                    f"Warning: 'reasoning_effort' parameter is not supported by the model '{model_name}'. "
                    f"This parameter is only compatible with the following models: {compatible_models}. "
                    f"The parameter has been ignored for this request."
                )
                print(warning_msg)
                warnings.warn(warning_msg)

            
        
        client = AzureOpenAI(
            api_key=model_config.get("api_key"),
            api_version=model_config.get("api_version"),
            azure_endpoint=model_config.get("azure_endpoint"),
            azure_deployment=model_config.get("azure_deployment"),
        )

        if supports_reasoning_summary:

            response = client.responses.create(
                input=prompt,
                model=model_config.get("model_id"), # replace with model deployment name
                reasoning={
                    "effort": kwargs.get("reasoning_effort"),
                    "summary": kwargs.get("summary_level", "detailed") # auto, concise, or detailed (currently only supported with o4-mini and o3)
                }
            )

            print(response)

            return {
                    "thinking": response.output[0].summary[0].text if response.output[0].summary else "",
                    "response": response.output[1].content[0].text
                }

        else:
        
            response = client.chat.completions.create(
                model=model_config.get("model_id"),
                messages=[{"role":"system", "content": system_prompt},
                        {"role": "user", "content": prompt}],
                **request_kwargs
            )
        
            return response.choices[0].message.content
