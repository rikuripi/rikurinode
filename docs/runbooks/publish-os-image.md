# Runbook — publish the node's OS image

Who: the owner. Where: GitHub's web page; no command line. How long: about
ten minutes, the VM drill included. What it does: builds the node's OS image from
`main`, checks it, boots it in a VM and runs the rollback drill (in which
the node also refuses an unsigned update and accepts a signed one), then
publishes it to `ghcr.io/rikuripi/rikurinode` under a new fixed name (for
example `44.20261028.3`: Fedora release, date, run number) and signs it with
the project's key. Publishing updates no node: a node never follows a tag
by itself, and is switched to a release's fixed name only when it is told
to (later, by the node's control plane). Workflow: `.github/workflows/publish.yml`; record:
`docs/build-records/2026-10-28-publish-signed-image.md`.

## Publish

1. On GitHub, open the repository's **Actions** tab, then **Publish the OS image** in the list on the left.
2. Click **Run workflow**, leave the branch on **main**, and click **Run workflow** again. Any other branch runs nothing.
3. Wait for its four jobs:
   - **Build, check, prove and drill one image, then push it**;
   - **Check it is the image built, refuse it unsigned, sign it, accept it**;
   - **A node reads it with no credential**;
   - **Build the USB installer from the signed digest, with no credential**.

   The run's summary page shows the fixed name and the image's digest. The fourth job keeps the install stick's file as the run's artifact **install-media**, for 90 days (`docs/runbooks/install-node.md`).

## The first publish only: make the package public

The package starts private, so on the first publish the third job fails and
says that the package is not public yet. That is expected.

1. Open `https://github.com/users/rikuripi/packages/container/rikurinode/settings`. You can also reach it from the repository's main page: under **Packages** on the right, open **rikurinode**, then **Package settings**.
2. Under **Danger Zone**, choose **Change visibility**, then **Public**, and confirm. **This cannot be undone** (decided: ADR 0004, D6). The image holds no secret by rule; the image checker and the gate's secret scan enforce this.
3. Wait a few minutes: the registry takes that long to serve a public package (2026-10-29). Then, on the run's page, click **Re-run jobs**, then **Re-run failed jobs**. Only the third job runs again, and it should pass.

## When a job fails

- **The first or the second job** (build, check, drill, push, or signing): do not re-run it. Start a new publish once the cause is fixed on `main`.
  - The first job refuses a re-run, because a re-run would put a different image under the same fixed name.
  - The second job refuses one once the image is signed, because its check that the image is still unsigned then fails.
  - A name left unsigned is refused by every node, and a name signed whose checks did not finish is never used: nodes do not follow fixed names.
- **The third job**, after the first publish: a node cannot read the image. Report it; do not change the package's settings.
- **The fourth job**: the image is published and signed, but this run made no install stick. Report it; start no new publish for it.

Never paste the signing key or its password anywhere. Only the second job reads them, from the Environment `image-publish`.
