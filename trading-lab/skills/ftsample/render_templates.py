"""Render freqtrade's own default templates ('minimal' and 'full') into strategy files, using freqtrade's own
deploy_new_strategy (same as `freqtrade new-strategy --template minimal|full`). No network."""
import pathlib
from freqtrade.commands.deploy_commands import deploy_new_strategy
d = pathlib.Path(__file__).parent / "rendered"; d.mkdir(exist_ok=True)
for sub, name in (("minimal", "FtMinimal"), ("full", "FtFull")):
    deploy_new_strategy(name, d / f"{name}.py", sub)
