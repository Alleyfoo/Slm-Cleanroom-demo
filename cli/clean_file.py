import json
from pathlib import Path
import click

from app.pipeline import run_pipeline


@click.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.option('-o', '--output', type=click.Path(), help='Output JSON file')
def main(input_path, output):
    text = Path(input_path).read_text(encoding='utf-8')
    result = run_pipeline(text)
    out_json = json.dumps(result, ensure_ascii=False, indent=2)
    if output:
        Path(output).write_text(out_json, encoding='utf-8')
    clean_path = Path(input_path).with_name(Path(input_path).stem + '-clean.txt')
    clean_path.write_text(result['clean_text'], encoding='utf-8')
    click.echo(out_json)


if __name__ == '__main__':
    main()
