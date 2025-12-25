
import os
import sys
import yaml
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from tools.cli.commands import init
from argparse import Namespace

@pytest.fixture
def mock_template_yaml():
    return """
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Parameters:
  Prefix:
    Type: String
    Default: dev
    Description: Environment prefix
  AccessLogGroup:
    Type: String
    Default: /aws/lambda/access-logs
"""

@pytest.fixture
def mock_generator_yaml():
    return """
app:
  name: ""
  tag: latest
paths:
  sam_template: /abs/path/to/template.yaml
  output_dir: /abs/path/to/.esb
  functions_yml: /abs/path/to/.esb/config/functions.yml
  routing_yml: /abs/path/to/.esb/config/routing.yml
parameters:
  Prefix: dev
  AccessLogGroup: /aws/lambda/access-logs
"""

def test_init_aborts_without_template(capsys):
    """テンプレートが見つからない・指定されない場合は終了すること"""
    with patch("tools.cli.commands.init.questionary.path") as mock_prompt, \
         patch("tools.cli.commands.init.cli_config.TEMPLATE_YAML", None), \
         patch("tools.cli.commands.init.Path.exists", return_value=False):
        
        mock_prompt.return_value.ask.return_value = None  # User cancels
        
        args = Namespace(template=None)
        with pytest.raises(SystemExit) as exc:
            init.run(args)
        assert exc.value.code == 1

def test_init_happy_path(mock_template_yaml, tmp_path):
    """正常系: テンプレートを読み込み、入力に基づいて設定ファイルを生成する"""
    template_file = tmp_path / "template.yaml"
    template_file.write_text(mock_template_yaml)
    
    # Mock user inputs: 
    # 1. Parameter: Prefix -> "prod"
    # 2. Parameter: AccessLogGroup -> (default)
    # 3. Image Tag -> "v1.0"
    # 4. Output Dir -> (default)
    # 5. Overwrite confirmation -> True (if needed)

    with patch("tools.cli.commands.init.questionary.text") as mock_text, \
         patch("tools.cli.commands.init.questionary.path") as mock_path, \
         patch("tools.cli.commands.init.cli_config.TEMPLATE_YAML", template_file):
        
        # Sequence of user inputs
        mock_text.return_value.ask.side_effect = ["prod", "/aws/lambda/access-logs", "v1.0"]
        mock_path.return_value.ask.return_value = str(tmp_path / ".esb")

        args = Namespace(template=str(template_file))
        init.run(args)

    # Verify generator.yml content
    gen_file = tmp_path / "generator.yml"
    assert gen_file.exists()
    
    with open(gen_file) as f:
        config = yaml.safe_load(f)
    
    assert config["app"]["tag"] == "v1.0"
    assert config["parameters"]["Prefix"] == "prod"
    assert config["parameters"]["AccessLogGroup"] == "/aws/lambda/access-logs"
    # Now generates portable relative path, not absolute
    assert config["paths"]["sam_template"] == "template.yaml"
