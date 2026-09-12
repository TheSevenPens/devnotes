# Windows pen behaviors

There are two sets of thing Windows does that is special when a pen is involved:

* It shows visual feedback
* It enables new system gestures

| What you see                                                     | Type                           |
| ---------------------------------------------------------------- | ------------------------------ |
| Ripple ring on every **tap - this is called "Dynamic feedback"** | **Visual feedback** (cosmetic) |
| Press-and-hold **ring** animation                                | **Visual feedback** (cosmetic) |
| Press-and-hold **right-click** (the behavior)                    | **System gesture**             |

The reason why it does this - is historical and I won't cover it here. But in short Microsoft has for decades tried to incorporate a seamless experience with touch and pen input as part of what it original called the "Tablet PC" concept.

The intention is noble, the execution is problematic. Very problematic for artists.

These visual effects and feedback are largely unwelcome by artists because they are (1) distracting , (2) actively interfere with drawing and (3) cause issues when interacting with interface elements such as sliders.

In this section we will clearly identify these behaviors, and show how to disable them programmatically.

{% hint style="info" %}
**Before you try to disable anything, check the baseline.** Whether Windows even _produces_ these behaviors depends on system-wide settings and on the input device — an indirect pen tablet often does not cause Windows to show shell feedback at all. See [Windows pen & touch settings](windows-pen-touch-settings.md). Working, toggleable demo apps for every behavior in this section live in the [sample apps](/broken/pages/Id6XMACmcVWx2WQDRWrw).
{% endhint %}
