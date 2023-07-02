This repo helps us testing svxlink to make sure our patches still work.
View these pages  [here](https://hobbyscoop.github.io/svxlink-testing/).

## Versions under test

| branch name | points to                                                                                                                                                                       | description                                                                                                   | test results                             |
|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|------------------------------------------|
| master      | [source](https://github.com/sm0svx/svxlink)                                                                                                                                     | svxlink upstream master branch                                                                                | [report-master.html](report-master.html) |
| old         | [source](https://github.com/hsmade/hobbyscoop)                                                                                                                                  | patched, 2018 version of svxlink                                                                              | [report-old.html](report-old.html)       |
| hobbyscoop  | [source](https://github.com/hobbyscoop/svxlink/tree/hobbyscoop) / [diff with upstream master](https://github.com/sm0svx/svxlink/compare/master...hobbyscoop:svxlink:hobbyscoop) | patched, 2023 version of svxlink | [report-hobbyscoop.html](report-hobbyscoop.html)       |

## Todo
* see how we can take in echolink testing, as we have a patch for voter preference for that

## Run
Run the Github Action named `test`.

Or manually:
```bash
./scripts/build-images.sh <branch>
BRANCH=<branch> pytest
```
Where `<branch>` is either master (upstream), `hobbyscoop`, or `old`.
If the branch wasn't updated, there is no need to rerun `build-images.sh`.

## Remotes
These values are hard-coded

| name    | siglev | tone |
|---------|--------|------|
| remote1 | 1000   | 524  |
| remote2 | 30     | 588  |

# Current test results - failing tests
Patches loaded in hobbyscoop branch:
 * [update voter PTY on enable/disable of Rx](https://github.com/sm0svx/svxlink/commit/624f77f16c9ffa9069bbe0efd869a7dc6db2dab8)
 * [always send all fields to voter PTY](https://github.com/sm0svx/svxlink/commit/fd1ca7004e7b8824eaad2e079003227b0bb07e48)
 * [force close squelch on MUTE](https://github.com/sm0svx/svxlink/commit/2f8a0dbe2e92359eaa53feeb2f0fc855a988ad10)
 * branch SHA [fd1ca700](https://github.com/hobbyscoop/svxlink/commit/fd1ca7004e7b8824eaad2e079003227b0bb07e48)

## Summary
When comparing the 2018 patches against upstream master ([8493ff1](https://github.com/sm0svx/svxlink/commit/8493ff1c66236e1d058306a7105f7303e3285d90)),
the main difference is that with the 2018 patches the enabled state was responded to [in the voter](https://github.com/hsmade/svxlink/blob/master/src/svxlink/trx/Voter.cpp#L809) 
which [is not the case anymore in upstream](https://github.com/sm0svx/svxlink/blob/8493ff1c66236e1d058306a7105f7303e3285d90/src/svxlink/trx/Voter.cpp#L818).
Instead, in upstream the DISABLE command (which uses `MUTE_ALL`), stops the siglev and squelch updates from coming into the voter at all,
and the MUTE command (which uses `MUTE_CONTENT`) lets them through. 
Due to this, MUTE fails to make an active receiver inactive. It will stay selected, without any audio.

A receiver is disabled on MUTE as per [this code](https://github.com/sm0svx/svxlink/blob/master/src/svxlink/trx/Voter.cpp#L1392C5-L1392C17).
And then during selection of a new bestrx, it's disabled state is [taken into account](https://github.com/sm0svx/svxlink/blob/master/src/svxlink/trx/Voter.cpp#L751).
When issuing DISABLE on a remote, the 'deselection' is triggered by [setting the squelch state](https://github.com/sm0svx/svxlink/blob/master/src/svxlink/trx/NetRx.cpp#L256-L262)
and then [this code](https://github.com/sm0svx/svxlink/blob/master/src/svxlink/trx/Voter.cpp#L829) starts a vote.

To make sure an active receiver is 'deselected' when MUTE is issued, we can add `sql_is_open = false;` before [the break](https://github.com/sm0svx/svxlink/blob/8493ff1c66236e1d058306a7105f7303e3285d90/src/svxlink/trx/NetRx.cpp#L253).
This triggers the voter to call `findBestRx`, similarly to how this happens for DISABLE.
This however overrides the squelch state of the muted receiver, which introduces another problem:
if the now inactive receiver is enabled again, and the actual squelch on the receiver is still open, 
it is not selected by the voter, as the voter still thinks the squelch is closed after overriding it.

# The tests
The code for the tests can be found in [tests/test_original.py](tests/test_original.py).

## Running tests using MUTE command to silence remote
This is close to the 2018 patches, as it invokes `MUTE_CONTENT` (see [here]([here](https://github.com/hsmade/svxlink/blame/master/src/svxlink/trx/Voter.cpp#L192)).
However, the decisions made when a remote is muted, are different then in the 2018 patches.
The results are for the `hobbyscoop` branch.

### test_reselect_open_disable_enable
Test description: the voter should reselect if an open remote is enabled after disable
This works correctly with the 2018 patches.

Test sequence:
* open squelch for remote1
* mute remote1
* expect TX to be off
* enable remote1
* expect TX to be on and remote1 to be active

This fails in the last step. This happens because the squelch state is overwritten by NetRx.cpp function `NetRx::setMuteState`
when the receiver is muted. This is needed to deselect the receiver when it happens to be active, so a re-election is done
for the best RX.

### test_reselect_open_disable_enable_interrupt
Test description: the voter should reselect a receiver that is disabled and then enabled, if another receiver was selected during disable
This works correctly with the 2018 patches.

Test sequence:
* open squelch for remote1 and remote2
* expect TX to be on and remote1 to be selected (has higher siglev)
* mute remote1
* expect remote2 to be selected
* enable remote1
* expect remote1 to be re-selected because of higher siglev

This fails in the last step. This happens because the squelch state is overwritten by NetRx.cpp function `NetRx::setMuteState`
when the receiver is muted. This is needed to deselect the receiver when it happens to be active, so a re-election is done
for the best RX.
