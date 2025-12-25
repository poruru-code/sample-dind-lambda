import docker
import os
import sys
import yaml
from pathlib import Path
from tools.generator import main as generator
from tools.cli import config as cli_config
from tools.cli.core import logging

# Directory for ESB Lambda base image
RUNTIME_DIR = cli_config.PROJECT_ROOT / "tools" / "generator" / "runtime"
BASE_IMAGE_TAG = "esb-lambda-base:latest"


def build_base_image(no_cache=False):
    """Build the ESB Lambda base image."""
    client = docker.from_env()
    dockerfile_path = RUNTIME_DIR / "Dockerfile.base"

    if not dockerfile_path.exists():
        logging.warning(f"Base Dockerfile not found: {dockerfile_path}")
        return False

    logging.step("Building base image...")
    print(f"  • Building {logging.highlight(BASE_IMAGE_TAG)} ...", end="", flush=True)

    try:
        client.images.build(
            path=str(RUNTIME_DIR),
            dockerfile="Dockerfile.base",
            tag=BASE_IMAGE_TAG,
            nocache=no_cache,
            rm=True,
        )
        print(f" {logging.Color.GREEN}✅{logging.Color.END}")
        return True
    except Exception as e:
        print(f" {logging.Color.RED}❌{logging.Color.END}")
        logging.error(f"Base image build failed: {e}")
        return False


def _extract_function_name_from_dockerfile(dockerfile_path) -> str | None:
    """Extract FunctionName from Dockerfile."""
    try:
        with open(dockerfile_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("# FunctionName:"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def build_function_images(functions, template_path, no_cache=False, verbose=False):
    """
    Build images for each function.
    """
    client = docker.from_env()
    sam_template_path = Path(template_path)

    logging.step("Building function images...")

    for func in functions:
        function_name = func["name"]
        dockerfile_path = func.get("dockerfile_path")
        context_path = func.get("context_path")
        
        if not dockerfile_path or not Path(dockerfile_path).exists():
            logging.warning(f"Dockerfile not found for {function_name} at {dockerfile_path}")
            continue

        image_tag = f"{function_name}:latest"

        print(f"  • Building {logging.highlight(image_tag)} ...", end="", flush=True)
        try:
            # Build context is the generated staging directory (context_path)
            # Dockerfile name is fixed as "Dockerfile"
            client.images.build(
                path=str(context_path),
                dockerfile="Dockerfile",
                tag=image_tag,
                nocache=no_cache,
                rm=True,
            )
            print(f" {logging.Color.GREEN}✅{logging.Color.END}")
        except Exception as e:
            print(f" {logging.Color.RED}❌{logging.Color.END}")
            if verbose:
                logging.error(f"Build failed for {image_tag}: {e}")
                raise
            else:
                logging.error(f"Build failed for {image_tag}. Use --verbose for details.")
                import sys
                sys.exit(1)


def run(args):
    dry_run = getattr(args, "dry_run", False)
    verbose = getattr(args, "verbose", False)

    if dry_run:
        logging.info("Running in DRY-RUN mode. No files will be written, no images built.")

    # 1. Generate configuration files (Phase 1 Generator)
    logging.step("Generating configurations...")
    logging.info(f"Using template: {logging.highlight(cli_config.TEMPLATE_YAML)}")

    # Load Generator configuration
    # Prioritize generator.yml located in the same directory as the template
    config_path = cli_config.E2E_DIR / "generator.yml"

    if not config_path.exists():
        import questionary
        from tools.cli.commands import init

        print(f"ℹ Configuration file not found at: {config_path}")
        if questionary.confirm("Do you want to initialize configuration now?").ask():
            # Call Init command (Reuse current args, but pass template only)
            init_args = type('Args', (), {'template': str(cli_config.TEMPLATE_YAML)})
            init.run(init_args)
            # Could confirm to continue build after Init, but exit for now
            logging.info("Configuration initialized. Please run build command again.")
            return
        else:
            logging.error("Configuration file missing. Cannot proceed.")
            return

    config = generator.load_config(config_path)

    # Resolve template path
    if "paths" not in config:
        config["paths"] = {}
    config["paths"]["sam_template"] = str(cli_config.TEMPLATE_YAML)

    functions = generator.generate_files(
        config=config,
        project_root=cli_config.PROJECT_ROOT,
        dry_run=dry_run,
        verbose=verbose,
    )

    if dry_run:
        logging.success("Dry-run complete. Exiting.")
        return

    logging.success("Configurations generated.")

    # 2. Build base image
    no_cache = getattr(args, "no_cache", False)

    if not build_base_image(no_cache=no_cache):
        import sys

        sys.exit(1)

    # 3. Build Lambda function images
    build_function_images(
        functions=functions,
        template_path=cli_config.TEMPLATE_YAML,
        no_cache=no_cache,
        verbose=verbose,
    )

    logging.success("Build complete.")
