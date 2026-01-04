import sys

sys.path.append('.venv/lib/python3.12/site-packages')
from octave_mcp.core import lexer, parser, validator


def test_file(path):
    print(f'Testing {path}:')
    try:
        with open(path) as f:
            content = f.read()

        # Attempt tokenization
        tokens, repairs = lexer.tokenize(content)
        print('Tokens:')
        for token in tokens:
            print(f'  - {token.type}: {token.value}')

        # Attempt parsing
        doc, warnings = parser.parse_with_warnings(content)

        if warnings:
            print('Parsing Warnings:')
            for warning in warnings:
                print(f'  - {warning}')

        # Attempt validation (assuming a schema is available)
        schema = {'META': {'fields': {}, 'required': []}}
        validation_errors = validator.validate(doc, schema)

        if validation_errors:
            print('Validation Errors:')
            for err in validation_errors:
                print(f'  - {err.code}: {err.message} (at {err.field_path})')
        else:
            print('✓ No validation errors')
    except Exception as e:
        print(f'Error: {e}')
    print('---')

test_files = [
    '.hestai/octave-validation-tests/simple-test.oct.md',
    '.hestai/octave-validation-tests/nested-structure.oct.md',
    '.hestai/octave-validation-tests/value-types.oct.md',
    '.hestai/octave-validation-tests/special-chars.oct.md'
]

for file_path in test_files:
    test_file(file_path)
