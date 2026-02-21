from json import tool
import os
from typing import Any, Optional,List
from openai import AsyncOpenAI, RateLimitError, APIConnectionError, APIError
from dotenv import load_dotenv
from client.response import TextDelta,TokenUsage,StreamEvent,StreamEventType
from typing import AsyncGenerator
import asyncio
load_dotenv()

class LLMClient:

    def __init__(self):    
        self._client : Optional[AsyncOpenAI] = None
        self._max_retries : int = 3 

    def get_client(self) -> AsyncOpenAI:

        if self._client is None:
            self._client  = AsyncOpenAI(
                api_key=os.environ["OPENROUTER_API"],
                base_url= "https://openrouter.ai/api/v1"
            )

        return self._client
    
    async def close(self) -> None:
        if self._client:
            await self._client.close()
            self._client = None
            
            
    def _build_tools(self, tools: list[dict[str, Any]]):
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get(
                        "parameters",
                        {
                            "type": "object",
                            "properties": {},
                        },
                    ),
                },
            }
            for tool in tools
        ]


    async def chat_completion(self, messages : List[dict[str,Any]], 
                              tools : list[dict[str, Any]] | None = None,
                              stream : bool = True) -> AsyncGenerator[Optional[StreamEvent], None]:

        client = self.get_client()
        kwargs  ={"model":"nvidia/nemotron-nano-12b-v2-vl:free",
                "messages":messages,
                "stream" : stream}
        
        print(messages)
        if tools:
            kwargs['tools'] = self._build_tools(tools)
            kwargs['tool_choice'] = "auto"
        
        for attempt in range(self._max_retries+1):
            try:
                if stream:
                    async for event in self._stream_response(client, kwargs):
                        yield event
                else:
                    event = await self._non_stream_response(client, kwargs)
                    yield event
                return

            except RateLimitError as e:
                if attempt < self._max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    # yield StreamEvent(type=StreamEventType.ERROR,error=f"Rate limit exceeded : {e}")
                    yield StreamEvent.stream_error(error=f"Rate limit exceeded : {e}")

                    return
                
            except APIConnectionError as e:
                if attempt < self._max_retries:
                    wait_time = 2**attempt
                    await asyncio.sleep(wait_time)
                else:
                    yield StreamEvent.stream_error(error=f"Connection Error  : {e}")
                    # yield StreamEvent(type=StreamEventType.ERROR,error=f"Connection Error  : {e}")

                    return
                    
            except APIError as e:
               
                yield StreamEvent.stream_error(error=f"API Error  : {e}")
                # yield StreamEvent(type=StreamEventType.ERROR,error=f"API Error  : {e}")

                return

    async def _stream_response(self,client : AsyncOpenAI, kwargs : dict[str,Any]) ->AsyncGenerator[Optional[StreamEvent], None]:

        response = await client.chat.completions.create(**kwargs)

        usage : Optional[TokenUsage] = None
        finish_reason : Optional[str] = None

        async for chunk in response:
            if hasattr(chunk,"usage") and chunk.usage:
                usage = TokenUsage(
                prompt_tokens=chunk.usage.prompt_tokens,
                completion_tokens= chunk.usage.completion_tokens,
                total_tokens= chunk.usage.total_tokens,
                cached_tokens= chunk.usage.prompt_tokens_details.cached_tokens,
            )
            
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta

            if choice.finish_reason:
                finish_reason = choice.finish_reason
            if delta.content:
                yield StreamEvent(type=StreamEventType.TEXT_DELTA,
                                  text_delta=TextDelta(delta.content))
                
            print(delta.tool_calls)
        yield StreamEvent(type=StreamEventType.MESSAGE_COMPLETE,
                          finish_reason=finish_reason,
                          usage=usage)
                

    async def _non_stream_response(self,client : AsyncOpenAI, kwargs : dict[str,Any]):

        response = await client.chat.completions.create(**kwargs)
        print(response)
        print()

        choice = response.choices[0]
        message = choice.message

        text_delta, usage =  None, None

        if message.content:
            text_delta = TextDelta(content=message.content)
        if response.usage:
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens= response.usage.completion_tokens,
                total_tokens= response.usage.total_tokens,
                cached_tokens= response.usage.prompt_tokens_details.cached_tokens,
            )
        return StreamEvent(
            type=StreamEventType.TEXT_DELTA,
            text_delta=text_delta,
            finish_reason= choice.finish_reason,
            usage= usage)