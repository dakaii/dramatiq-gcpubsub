# Publishing

## 1. Create the GitHub repo

From the project root (with [GitHub CLI](https://cli.github.com/) installed and logged in):

```bash
git init
git add .
git commit -m "Initial commit: dramatiq-gcpubsub broker"
gh repo create dramatiq-gcpubsub --public --source=. --remote=origin --push
```

If the repo already exists elsewhere or you use a different owner:

```bash
gh repo create YOUR_ORG/dramatiq-gcpubsub --public --source=. --remote=origin --push
```

## 2. Publish to PyPI (one-time setup)

The workflow in `.github/workflows/publish.yml` publishes to PyPI when you **create a GitHub release**. No API tokens in the repo are needed if you use **trusted publishing**.

### Option A: Trusted publishing (recommended)

1. Create a PyPI account at https://pypi.org/account/register/ if you don’t have one.
2. Create the project on PyPI (or it will be created on first publish):  
   https://pypi.org/manage/project/new/  
   - Project name: `dramatiq-gcpubsub`
3. Add a trusted publisher:  
   https://pypi.org/manage/project/dramatiq-gcpubsub/settings/publishing/
   - **Publisher**: GitHub
   - **Owner**: your GitHub username or org (e.g. `dakaii`)
   - **Repository**: `dramatiq-gcpubsub`
   - **Workflow name**: `publish.yml`
   - **Environment**: leave empty
4. Save. Future runs of the `publish.yml` workflow (on release) will publish without any secrets.

### Option B: API token (alternative)

If you prefer not to use trusted publishing:

1. On PyPI: Account → API tokens → Add API token (scope: entire account or just this project).
2. In GitHub: repo → Settings → Secrets and variables → Actions → New repository secret:
   - Name: `PYPI_API_TOKEN`
   - Value: your token
3. In `.github/workflows/publish.yml`, replace the publish step with:

   ```yaml
   - name: Publish to PyPI
     uses: pypa/gh-action-pypi-publish@release
     with:
       password: ${{ secrets.PYPI_API_TOKEN }}
   ```

## 3. Releasing a new version

1. Bump the version in `pyproject.toml` (`version = "0.1.0"` → e.g. `"0.1.1"`).
2. Commit and push:

   ```bash
   git add pyproject.toml
   git commit -m "Bump version to 0.1.1"
   git push
   ```

3. Create a GitHub release (tag = version):

   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```

   Then on GitHub: Releases → Draft a new release → choose tag `v0.1.1`, add release notes, publish.

   Or with `gh`:

   ```bash
   gh release create v0.1.1 --generate-notes
   ```

4. The **Publish to PyPI** workflow runs automatically. When it succeeds, the package is on https://pypi.org/project/dramatiq-gcpubsub/.

### TestPyPI first (optional)

To try the pipeline without publishing to real PyPI:

1. Add a trusted publisher (or token) for TestPyPI: https://test.pypi.org/manage/account/ .
2. Duplicate the workflow (e.g. `publish-test.yml`) and set:

   ```yaml
   - name: Publish to TestPyPI
     uses: pypa/gh-action-pypi-publish@release
     with:
       repository-url: https://test.pypi.org/legacy/
   ```

   For TestPyPI with trusted publishing, configure the publisher at TestPyPI’s project settings.

3. Trigger that workflow (e.g. on a tag like `v0.1.1-test` or via `workflow_dispatch`), then install with:

   ```bash
   pip install -i https://test.pypi.org/simple/ dramatiq-gcpubsub
   ```
