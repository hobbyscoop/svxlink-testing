This repo helps us testing svxlink to make sure our patches still work.

## Todo
* write tests
  * see how we can take in echolink testing, as we have a patch for voter preference for that
  * see if/how we can verify the selected remote from the audio
* GitHub actions

## Run
* run the Github Action named `test`, select the branch to test:
  * `master`: svxlink upstream
  * `hobbyscoop`: with hobbyscoop patches
  * `old`: old repo with patches

Or manually:
```bash
./scripts/build-images.sh <branch>
BRANCH=<branch> pytest
```
Where `<branch>` is either master (upstream) or `hobbyscoop`.
If the branch wasn't updated, there is no need to rerun `build-images.sh`.

## Remotes
These values are hard-coded

| name    | siglev | tone |
|---------|--------|------|
| remote1 | 1000   | 524  |
| remote2 | 30     | 588  |
