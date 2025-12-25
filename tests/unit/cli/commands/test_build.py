
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from tools.cli.commands import build
from argparse import Namespace

@pytest.fixture
def mock_cli_config(tmp_path):
    with patch("tools.cli.commands.build.cli_config") as mock:
        mock.E2E_DIR = tmp_path
        mock.TEMPLATE_YAML = tmp_path / "template.yaml"
        mock.PROJECT_ROOT = tmp_path
        yield mock

def test_build_redirects_to_init_when_config_missing_and_confirmed(mock_cli_config):
    """generator.ymlがない場合、ユーザーがYesを選択すればinitが呼ばれる"""
    
    # args mock
    args = Namespace(dry_run=False, verbose=False, no_cache=False)
    
    with patch("questionary.confirm") as mock_confirm, \
         patch("tools.cli.commands.init.run") as mock_init_run, \
         patch("tools.cli.commands.build.generator.load_config") as mock_load_config, \
         patch("tools.cli.commands.build.generator.generate_files"), \
         patch("tools.cli.commands.build.build_base_image"), \
         patch("tools.cli.commands.build.build_function_images"):

        # Confirm -> Yes
        mock_confirm.return_value.ask.return_value = True
        
        # init 完了後に一旦 return する実装になっているので、load_configなどは呼ばれないはず
        # ただし、init.run 内でファイルが作られるわけではないので(mockなので)、
        # redirect 後にreturnすることを検証する
        
        build.run(args)
        
        # init.run が呼ばれたか
        mock_init_run.assert_called_once()
        # 引数のtemplateが正しく渡されているか
        call_args = mock_init_run.call_args[0][0]
        assert call_args.template == str(mock_cli_config.TEMPLATE_YAML)

def test_build_aborts_when_config_missing_and_cancelled(mock_cli_config):
    """generator.ymlがない場合、ユーザーがNoを選択すれば終了する"""
    
    args = Namespace(dry_run=False, verbose=False, no_cache=False)
    
    with patch("questionary.confirm") as mock_confirm, \
         patch("tools.cli.commands.init.run") as mock_init_run:
        
        # Confirm -> No
        mock_confirm.return_value.ask.return_value = False
        
        build.run(args)
        
        # init.run は呼ばれない
        mock_init_run.assert_not_called()
