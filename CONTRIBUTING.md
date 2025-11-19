# Development - Contributing

Issues and pull requests are more than welcome.

We recommand using [`uv`](https://docs.astral.sh/uv) as project manager for development.

See https://docs.astral.sh/uv/getting-started/installation/ for installation 

### dev install

```
git clone http://github.com/developmentseed/cogeo-mosaic.git
cd cogeo-mosaic

uv sync --all-extras
```

You can then run the tests with the following command:

```sh
uv run pytest  --cov cogeo_mosaic --cov-report term-missing
```

### pre-commit

This repo is set to use `pre-commit` to run *isort*, *flake8*, *pydocstring*, *black* ("uncompromising Python code formatter") and mypy when committing new code.

```bash
uv run pre-commit install

git add .

git commit -m'my change'
isort....................................................................Passed
black....................................................................Passed
Flake8...................................................................Passed
Verifying PEP257 Compliance..............................................Passed
mypy.....................................................................Passed

git push origin
```

### Docs

```bash
git clone https://github.com/developmentseed/cogeo-mosaic.git
cd cogeo-mosaic
```

Hot-reloading docs:

```bash
uv run --group docs mkdocs serve -f docs/mkdocs.yml
```

To manually deploy docs (note you should never need to do this because Github
Actions deploys automatically for new commits.):

```bash
uv run --group docs mkdocs gh-deploy -f docs/mkdocs.yml
```
