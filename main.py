import asyncio
from typing import Optional, Any
import click
import sys
from agent.agent import Agent
from agent.event import AgentEventType
from ui.tui import TUI,get_console


console = get_console()
class CLI:

    def __init__(self):
        self.agent = Optional[Agent]
        self.tui = TUI(console)

    async def run_single(self,message : str) -> Optional[str]:
        async with Agent() as agent:
            self.agent = agent
            return await self._process_message(message)

    async def _process_message(self,message : str) -> Optional[str]:
        if not self.agent:
            return None
        
        assistant_streaming = False
        final_response  = None
        
        async for event in self.agent.run(message):
            if event.type == AgentEventType.TEXT_DELTA:
                content = event.data.get("content","")
                if not assistant_streaming:
                    self.tui.begin_assistant()
                    assistant_streaming = True
                self.tui.stream_assistant_delta(content)
            elif event.type == AgentEventType.TEXT_COMPLETE:
                final_response = event.data.get("content")
                if assistant_streaming:
                    self.tui.end_assistant()
                    assistant_streaming = False

            elif event.type == AgentEventType.AGENT_ERROR:
                error = event.data.get("error","Unknown Error")
                console.print(f"\n[error]Error : {error}[/error]")

        return final_response

            

@click.command()
@click.argument("prompt",required=False)
def main(
    prompt : Optional[str],
):  
    print(prompt)
    cli = CLI()
    # messages = [{"role":"user","content":prompt}]
    if prompt:
        result = asyncio.run(cli.run_single(prompt))
        if result is None:
            sys.exit(1)
    print('done')   

main()