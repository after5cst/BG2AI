## BG2AI
Customization of Baldur's Gate 2 EE Script BDDEFAI.BCS

This contains the text behind BDDEFAI.TXT.  As I change it for my own needs
it will provide a history of the changes.

## Comments

* The script does a lot of good things, with conditions for casting a
  great variety of spells.

* No offense, but scripts aren't that good at figuring out the "right"
  time to cast spells.  The default does silly things like burn a
  Mirror Image even though there's only one enemy with 3 HP left.  This
  is not an indictment of the script writer: the engine itself doesn't
  lend itself easily to figuring out when to hold back, etc.

* Also, I like choosing the spells (for the most part).  What I don't
  care for is micromanaging the melee actions (and ranged), since they
  are usually pretty mundane.  However, the original script doesn't spend
  hardly any time on weapon selection or usage... which is what I would
  rather not mess with.

* And lastly, I'd rather modify what they have hear because the script
  does deal with one thing (which spell is used to counter which defense)
  that I'd rather not take the time to memorize and learn with all then
  weird combinations.
  
## Behavior

### Hotkeys

* F - Enable follow mode on a character.  Pressing F will cycle through
      visible targets looking for the next leader (person to follow).
      Selecting yourself as leader effectively disables following.
      
* D - Enable healing mode.  While in healing mode, the character will
      work to heal the most damaged character.  After the character 
      no longer has a good match for the most damaged character,
      the character will exit healing mode.

## Changes

* Moved ActionListEmpty to the top of blocks and made it required.  This
  allows the user to "be in control" : if an action is in progress it will
  not be interrupted by the script.
  
* Moved HaveSpell() to the top of the control block underneath 
  ActionListEmpty().  This should (I think) largely improve AI CPU usage 
  since in many cases a character won't have the spell required for the 
  block without any kind of string check.

## HELPFUL NOTES:

### BDAI_RESET_TIMERS

It doesn't seem to be driven by the GUI in any meaningful way.  I believe
that it is only used by the script itself as a "have I ever been
initialized" timer.

### BDAI_SKILL_MODE (settable in GUI):
* 0 == Not Set

* 1 == Find Traps

* 2 == Hide in Shadows

* 3 == Bard Song

* 4 == Turn Undead


### BDAI_ATTACK_MODE (settable in GUI):
* 0 == Not Set

* 1 == Prefer Melee

* 2 == Prefer Ranged

### AI Script Slots

Looks like CLASS is used for player-picked scripts, and RACE is
available for use.  The others will (possibly) conflict with other
things that can happen in-game.

* CLASS -- Player1 set to BDDEFAI by area at start of game
* DEFAULT -- Set by AI scripts.  Used on party members
* GENERAL -- Set by AI scripts.  Used on party members
* SPECIFICS -- Set by AI scripts.  Used on party members
* OVERRIDE -- Set by AI scripts.  Used on party members
* RACE -- Set by AI scripts.

