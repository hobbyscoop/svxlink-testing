This repo helps us testing svxlink to make sure our patches still work.

## Todo
* write tests
  * see how we can take in echolink testing, as we have a patch for voter preference for that

## Run
* run the Github Action named `test`, select the branch to test:
  * `master`: [svxlink upstream](https://github.com/sm0svx/svxlink)
  * `hobbyscoop`: with hobbyscoop patches ([changes from master](https://github.com/sm0svx/svxlink/compare/master...hobbyscoop:svxlink:hobbyscoop))
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

# Current test results - failing tests
Patches loaded:
 * [update voter PTY on enable/disable of Rx](https://github.com/sm0svx/svxlink/commit/12d0676785bcbf1c4b4297428ebd314f39ffd935)

## using DISABLE command to silence remote
This invokes `MUTE_ALL`, which isn't what we were doing in the 2018 patches.

### tests/test_original.py::Test::test_reselect_open_disable_enable_interrupt - AssertionError: False != True : remote1 should become active
Test description: the voter should reselect a remote that is disabled and then enabled, if another remote was selected during disable.
This works correctly with the 2018 patches.

Test sequence:
* open squelch for remote 1 and 2
* disable remote 1 ([which closes the squelch](https://github.com/sm0svx/svxlink/blob/8493ff1c66236e1d058306a7105f7303e3285d90/src/svxlink/trx/NetRx.cpp#L258))
* expect remote 2 to be selected
* enable remote 1
* expect remote 1 to be reselected (has higher siglev) <- fails

#### Reason
This seems intentional, as the remote is disabled, so the sql events are not coming through.

### tests/test_original.py::Test::test_select_disable_open_enable - AssertionError: False != True : transmitter should be on
Test description: the voter should select if a disabled remote is opened and enabled.
This works correctly with the 2018 patches.

Test sequence:
* disable remote 1
* open squelch on remote 1 (which signal doesn't arrive as the remote is disabled)
* enable remote 1
* expect transmitter to open TX <- fails

#### Reason
This seems intentional, as the remote is disabled
The NetRx [ignores the squelch update when disabled](https://github.com/sm0svx/svxlink/blob/8493ff1c66236e1d058306a7105f7303e3285d90/src/svxlink/trx/NetRx.cpp#L443)
Which implies that the idea of sm0svx is to use mute for this, not disable.
This is then not ending up [here](https://github.com/sm0svx/svxlink/blob/8493ff1c66236e1d058306a7105f7303e3285d90/src/svxlink/trx/Voter.cpp#L650),

## using MUTE command to silence remote
This is closed to the 2018 patches, as it invokes `MUTE_CONTENT` (see [here]([here](https://github.com/hsmade/svxlink/blame/master/src/svxlink/trx/Voter.cpp#L192)).
However, the decisions made when a remote is muted, are different then in the 2018 patches.

### tests/test_original.py::Test::test_disable_unselect_off - AssertionError: False != True : transmitter should be off
Test description: the voter should unselect a remote that is disabled
This works correctly with the 2018 patches.

Test sequence:
* open squelch for remote 1
* mute remote 1
* expect the TX to close <- fails

#### Reason
The `MUTE_CONTENT` only mutes the audio, but doesn't stop squelch or siglev signals from coming through.

### tests/test_original.py::Test::test_disable_unselect_switchover - AssertionError: False != True : remote2 should become active
Test description: the voter should switch over to another remote if the active remote is disabled
This works correctly with the 2018 patches.

Test sequence:
* open squelch for remote 1 (with higher siglev)
* open squelch for remote 2
* mute remote 1
* expect remote 2 to become selected <- fails: sticks with remote 1

#### Reason
The `MUTE_CONTENT` only mutes the audio, but doesn't stop squelch or siglev signals from coming through.

### tests/test_original.py::Test::test_reselect_open_disable_enable_interrupt - AssertionError: False != True : remote2 should become active
Test description: the voter should reselect a remote that is disabled and then enabled, if another remote was selected during disable
This works correctly with the 2018 patches.

Test sequence:
* open squelch for remote 1 and 2
* mute remote 1
* expect remote 2 to be selected <- fails here, unless the sql is set to off in NetRx on mute
* enable remote 1
* expect remote 1 to be reselected (has higher siglev) <- fails here

#### Reason
Remote isn't deselected because its squelch isn't closed. If this is fixed by modifying NetRx, 
the next problem is that remote 1 isn't reselected, because it's squelch is still off.

## Summary
When comparing the 2018 patches against master (2023), the main difference is that in the 2018 patches the enabled state
was responded to [in the voter](https://github.com/hsmade/svxlink/blob/master/src/svxlink/trx/Voter.cpp#L809) where this
[is not the case anymore in 2023](https://github.com/sm0svx/svxlink/blob/master/src/svxlink/trx/Voter.cpp#L818).
Instead, in 2023 the disabled state (which uses `MUTE_ALL`), stops the siglev and squelch updates from coming into the voter.
and the mute state (which uses `MUTE_CONTENT`), lets them through, but fails to deselect the remote.

A remote is in fact disabled on mute as per [this code](https://github.com/sm0svx/svxlink/blob/master/src/svxlink/trx/Voter.cpp#L1392C5-L1392C17).
And then during selection of a new bestrx, is [taken into account](https://github.com/sm0svx/svxlink/blob/master/src/svxlink/trx/Voter.cpp#L751).
When *disabling* a remote, the deselection is triggered by [setting the squelch state](https://github.com/sm0svx/svxlink/blob/master/src/svxlink/trx/NetRx.cpp#L256-L262)
and then [this code](https://github.com/sm0svx/svxlink/blob/master/src/svxlink/trx/Voter.cpp#L829) starts a vote.
This only works if the squelch is closed, though.

When adding `sql_is_open = false;` before [the break](https://github.com/sm0svx/svxlink/blob/8493ff1c66236e1d058306a7105f7303e3285d90/src/svxlink/trx/NetRx.cpp#L253)
the active Rx gets demoted correctly on *mute*.
However `test_reselect_open_disable_enable_interrupt` still fails, but later in the test. Now it still won't reselect remote 1 after it's
enabled without a new squelch event, as the original squelch isn't stored. 
