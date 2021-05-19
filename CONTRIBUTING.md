# Development - Contributing

Issues and pull requests are more than welcome.

**Dev install & Pull-Request**

```
$ git clone http://github.com/developmentseed/cogeo-mosaic.git
$ cd cogeo-mosaic
$ pip install -e .[dev]
```


**Python >=3.7 only**

This repo is set to use `pre-commit` to run *isort*, *flake8*, *pydocstring*, *black* ("uncompromising Python code formatter") and mypy when committing new code.

```
$ pre-commit install

$ git add .

$ git commit -m'my change'
isort....................................................................Passed
black....................................................................Passed
Flake8...................................................................Passed
Verifying PEP257 Compliance..............................................Passed
mypy.....................................................................Passed

$ git push origin
```

### Docs

```bash
$ git clone https://github.com/developmentseed/cogeo-mosaic.git
$ cd cogeo-mosaic
$ pip install -e .["docs"]
```

Hot-reloading docs:

```bash
$ mkdocs serve
```

To manually deploy docs (note you should never need to do this because Github
Actions deploys automatically for new commits.):

```bash
$ mkdocs gh-deploy
```
