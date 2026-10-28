# Runbook — publish the node's OS image

Who: the owner. Where: GitHub's web page; no command line. How long: about
two hours, mostly the VM drill. What it does: builds the node's OS image from
`main`, checks it, boots it in a VM and runs the rollback drill, then
publishes it to `ghcr.io/rikuripi/rikurinode` under a new fixed name (for
example `44.20261028.3`: Fedora release, date, run number) and signs it with
the project's key. Nodes do not follow these fixed names: publishing one
updates no node. Workflow: `.github/workflows/publish.yml`; record:
`docs/build-records/2026-10-28-publish-signed-image.md`.

## Publish

1. On GitHub, open the repository's **Actions** tab, then **Publish the OS image** in the list on the left.
2. Click **Run workflow**, leave the branch on **main**, and click **Run workflow** again. Any other branch runs nothing.
3. Wait for its three jobs:
   - **Build, check, prove and drill one image, then push it**;
   - **Check it is the image built, refuse it unsigned, sign it, accept it**;
   - **A node reads it with no credential**.

   The run's summary page shows the fixed name and the image's digest.

## The first publish only: make the package public

The package starts private, so on the first publish the third job fails and
says that the package is not public yet. That is expected.

1. Open `https://github.com/orgs/rikuripi/packages/container/rikurinode/settings`. You can also reach it from the repository's main page: under **Packages** on the right, open **rikurinode**, then **Package settings**.
2. Under **Danger Zone**, choose **Change visibility**, then **Public**, and confirm. **This cannot be undone** (decided: ADR 0004, D6). The image holds no secret by rule; the image checker and the gate's secret scan enforce this. If **Public** cannot be chosen, the organization does not allow public packages yet: in the organization's **Settings**, under **Packages**, allow **Public**, then come back.
3. Back on the run's page, click **Re-run jobs**, then **Re-run failed jobs**. Only the third job runs again, and it should pass.

## When a job fails

- **The first job** (build, check, drill or push): do not re-run it. It refuses a re-run, because a re-run would put a different image under the same fixed name. Start a new publish once the cause is fixed on `main`. A name that was pushed and never signed is refused by every node.
- **The second job** (signing): **Re-run failed jobs** is safe. It signs the same image again.
- **The third job**, after the first publish: a node cannot read the image. Report it; do not change the package's settings.

Never paste the signing key or its password anywhere. Only the second job reads them, from the Environment `image-publish`.
