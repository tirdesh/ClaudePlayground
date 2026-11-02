#!/usr/bin/env python3
"""Build the "Charge Check" iOS Shortcut (.shortcut, unsigned).

What the shortcut does:
  1. Goes to the Home Screen, screenshots it, and reads the Batteries widget
     percentages with on-device text recognition.
  2. Skips the first percentage (the iPhone) and flags any other device
     (Apple Watch / AirPods) below LOW_LEVEL.
  3. If something is low (or the widget could not be read) it asks:
       Charging now / Remind me in 30 min / Skip
  4. "Charging now" asks which devices you put on the pad, then creates a
     Reminder that alerts you after the estimated charge time.

Usage:
  python3 build_shortcut.py            # writes Charge Check.shortcut
Then sign it on a Mac (iOS refuses unsigned files):
  shortcuts sign --mode anyone --input "Charge Check.shortcut" \
      --output "Charge Check (signed).shortcut"
"""

import plistlib
import uuid
from pathlib import Path

# ---- Settings you may want to change -------------------------------------
SHORTCUT_NAME = "Charge Check"
LOW_LEVEL = 30            # percent; Watch/AirPods below this triggers the menu
WATCH_MINUTES = 60        # estimated charge time, Watch only
AIRPODS_MINUTES = 90      # estimated charge time when AirPods are on the pad
SNOOZE_MINUTES = 30
# ---------------------------------------------------------------------------

RUN_SELF_URL = "shortcuts://run-shortcut?name=" + SHORTCUT_NAME.replace(" ", "%20")
OBJ = "￼"  # placeholder char where a variable is inserted in text

# Condition codes used by the Shortcuts "If" action
COND_LESS_THAN = 0
COND_GREATER_THAN = 2
COND_CONTAINS = 99
COND_HAS_ANY_VALUE = 100
COND_NO_VALUE = 101


def uid():
    return str(uuid.uuid4()).upper()


# ---- variable references ----------------------------------------------------
def out_ref(action_uuid, name):
    """Reference to a previous action's output."""
    return {"Type": "ActionOutput", "OutputUUID": action_uuid, "OutputName": name}


def var_ref(name):
    """Reference to a named variable (also Repeat Item / Repeat Index)."""
    return {"Type": "Variable", "VariableName": name}


def current_date_ref():
    return {"Type": "CurrentDate"}


def attach(ref, aggrandizements=None):
    value = dict(ref)
    if aggrandizements:
        value["Aggrandizements"] = aggrandizements
    return {"Value": value, "WFSerializationType": "WFTextTokenAttachment"}


def text(*parts):
    """Build a text field from strings and variable refs (dicts)."""
    s = ""
    attachments = {}
    for p in parts:
        if isinstance(p, str):
            s += p
        else:
            ref, aggr = p if isinstance(p, tuple) else (p, None)
            value = dict(ref)
            if aggr:
                value["Aggrandizements"] = aggr
            attachments["{%d, 1}" % len(s)] = value
            s += OBJ
    if not attachments:
        return s
    return {
        "Value": {"string": s, "attachmentsByRange": attachments},
        "WFSerializationType": "WFTextTokenString",
    }


TIME_ONLY = [{
    "Type": "WFDateFormatVariableAggrandizement",
    "WFDateFormatStyle": "None",
    "WFTimeFormatStyle": "Short",
}]


# ---- action builder -----------------------------------------------------------
class Builder:
    def __init__(self):
        self.actions = []

    def add(self, ident, params=None, with_uuid=True):
        params = dict(params or {})
        u = uid()
        if with_uuid:
            params["UUID"] = u
        self.actions.append({
            "WFWorkflowActionIdentifier": "is.workflow.actions." + ident,
            "WFWorkflowActionParameters": params,
        })
        return u

    # control flow -----------------------------------------------------------
    def if_start(self, input_ref, condition, **extra):
        group = uid()
        params = {
            "GroupingIdentifier": group,
            "WFControlFlowMode": 0,
            "WFCondition": condition,
            "WFInput": {"Type": "Variable", "Variable": attach(input_ref)},
        }
        params.update(extra)
        self.add("conditional", params)
        return group

    def otherwise(self, group):
        self.add("conditional", {"GroupingIdentifier": group, "WFControlFlowMode": 1})

    def end_if(self, group):
        return self.add("conditional", {"GroupingIdentifier": group, "WFControlFlowMode": 2})

    def set_number_var(self, name, number):
        n = self.add("number", {"WFNumberActionNumber": number})
        self.add("setvariable", {"WFVariableName": name,
                                 "WFInput": attach(out_ref(n, "Number"))})

    def notify(self, title, body):
        self.add("notification", {"WFNotificationActionTitle": title,
                                  "WFNotificationActionBody": body})

    def reminder_at(self, title_text, date_uuid, notes):
        self.add("addnewreminder", {
            "WFCalendarItemTitle": title_text,
            "WFAlertEnabled": "Alert",
            "WFAlertCustomTime": text(out_ref(date_uuid, "Adjusted Date")),
            "WFCalendarItemNotes": notes,
        })

    def minutes_from_now(self, magnitude):
        """magnitude: int or a variable ref dict."""
        if isinstance(magnitude, dict):
            magnitude = attach(magnitude)
        return self.add("adjustdate", {
            "WFAdjustOperation": "Add",
            "WFDate": text(current_date_ref()),
            "WFDuration": {
                "Value": {"Magnitude": magnitude, "Unit": "min"},
                "WFSerializationType": "WFQuantityFieldValue",
            },
        })


def build():
    b = Builder()

    b.add("comment", {"WFCommentActionText":
                      "Charge Check: reads the Batteries widget (large, first Home Screen page, "
                      "iPhone listed first). Edit LOW level in the 'is less than' step and "
                      "charge minutes in the Minutes steps."})

    # 1. Read the Batteries widget -----------------------------------------
    b.add("returntohomescreen")
    b.add("delay", {"WFDelayTime": 1})
    shot = b.add("takescreenshot")
    ocr = b.add("extracttextfromimage", {"WFImage": attach(out_ref(shot, "Screenshot"))})
    matches = b.add("text.match", {
        "WFMatchTextPattern": r"\d+(?=\s*%)",
        "text": text(out_ref(ocr, "Text from Image")),
    })
    matches_ref = out_ref(matches, "Matches")

    # 2. Flag low devices, skipping the first entry (iPhone) -----------------
    rep_group = uid()
    b.add("repeat.each", {"GroupingIdentifier": rep_group, "WFControlFlowMode": 0,
                          "WFInput": attach(matches_ref)})
    g_idx = b.if_start(var_ref("Repeat Index"), COND_GREATER_THAN, WFNumberValue=1)
    num = b.add("detect.number", {"WFInput": attach(var_ref("Repeat Item"))})
    g_low = b.if_start(out_ref(num, "Numbers"), COND_LESS_THAN, WFNumberValue=LOW_LEVEL)
    b.add("appendvariable", {"WFVariableName": "Low",
                             "WFInput": attach(var_ref("Repeat Item"))})
    b.end_if(g_low)
    b.end_if(g_idx)
    b.add("repeat.each", {"GroupingIdentifier": rep_group, "WFControlFlowMode": 2})

    # 3. Decide whether to ask -------------------------------------------------
    g_none = b.if_start(matches_ref, COND_NO_VALUE)
    t = b.add("gettext", {"WFTextActionText": "Couldn't read the Batteries widget."})
    b.add("setvariable", {"WFVariableName": "Ask", "WFInput": attach(out_ref(t, "Text"))})
    b.end_if(g_none)

    g_haslow = b.if_start(var_ref("Low"), COND_HAS_ANY_VALUE)
    combined_low = b.add("text.combine", {"text": attach(var_ref("Low")),
                                          "WFTextSeparator": "Custom",
                                          "WFTextCustomSeparator": "%, "})
    t2 = b.add("gettext", {"WFTextActionText":
                           text("Low battery: ", out_ref(combined_low, "Combined Text"), "%")})
    b.add("setvariable", {"WFVariableName": "Ask", "WFInput": attach(out_ref(t2, "Text"))})
    b.end_if(g_haslow)

    # 4. Ask, or report all good ---------------------------------------------
    g_ask = b.if_start(var_ref("Ask"), COND_HAS_ANY_VALUE)

    menu = uid()
    items = ["Charging now", "Remind me in %d min" % SNOOZE_MINUTES, "Skip"]
    b.add("choosefrommenu", {"GroupingIdentifier": menu, "WFControlFlowMode": 0,
                             "WFMenuPrompt": text(var_ref("Ask"),
                                                  " Charge Watch & AirPods?"),
                             "WFMenuItems": items})

    # 4a. Charging now
    b.add("choosefrommenu", {"GroupingIdentifier": menu, "WFControlFlowMode": 1,
                             "WFMenuItemTitle": items[0]})
    lst = b.add("list", {"WFItems": ["Apple Watch", "AirPods"]})
    chosen = b.add("choosefromlist", {
        "WFInput": attach(out_ref(lst, "List")),
        "WFChooseFromListActionPrompt": "What did you put on the pad?",
        "WFChooseFromListActionSelectMultiple": True,
    })
    combined_chosen = b.add("text.combine", {"text": attach(out_ref(chosen, "Chosen Item")),
                                             "WFTextSeparator": "Custom",
                                             "WFTextCustomSeparator": " & "})
    devices_ref = out_ref(combined_chosen, "Combined Text")
    g_pods = b.if_start(devices_ref, COND_CONTAINS, WFConditionalActionString="AirPods")
    b.set_number_var("Minutes", AIRPODS_MINUTES)
    b.otherwise(g_pods)
    b.set_number_var("Minutes", WATCH_MINUTES)
    b.end_if(g_pods)
    done_at = b.minutes_from_now(var_ref("Minutes"))
    b.reminder_at(text("Take ", devices_ref, " off the pad 🔌"), done_at,
                  text("Tap to check levels: ", RUN_SELF_URL))
    b.notify("Charging", text("I'll remind you at ",
                              (out_ref(done_at, "Adjusted Date"), TIME_ONLY)))

    # 4b. Snooze
    b.add("choosefrommenu", {"GroupingIdentifier": menu, "WFControlFlowMode": 1,
                             "WFMenuItemTitle": items[1]})
    later = b.minutes_from_now(SNOOZE_MINUTES)
    b.reminder_at("Charge Watch & AirPods", later,
                  text("Tap to run Charge Check: ", RUN_SELF_URL))

    # 4c. Skip
    b.add("choosefrommenu", {"GroupingIdentifier": menu, "WFControlFlowMode": 1,
                             "WFMenuItemTitle": items[2]})

    b.add("choosefrommenu", {"GroupingIdentifier": menu, "WFControlFlowMode": 2})

    b.otherwise(g_ask)
    all_good = b.add("text.combine", {"text": attach(matches_ref),
                                      "WFTextSeparator": "Custom",
                                      "WFTextCustomSeparator": "%, "})
    b.notify("All good 🔋", text(out_ref(all_good, "Combined Text"), "%"))
    b.end_if(g_ask)

    return {
        "WFWorkflowActions": b.actions,
        "WFWorkflowClientVersion": "2302.0.4",
        "WFWorkflowMinimumClientVersion": 900,
        "WFWorkflowMinimumClientVersionString": "900",
        "WFWorkflowIcon": {"WFWorkflowIconStartColor": 4292093695,   # green
                           "WFWorkflowIconGlyphNumber": 59511},
        "WFWorkflowImportQuestions": [],
        "WFWorkflowInputContentItemClasses": [],
        "WFWorkflowTypes": [],
        "WFWorkflowHasOutputFallback": False,
        "WFWorkflowHasShortcutInputVariables": False,
        "WFWorkflowOutputContentItemClasses": [],
        "WFQuickActionSurfaces": [],
    }


if __name__ == "__main__":
    out = Path(__file__).with_name(SHORTCUT_NAME + ".shortcut")
    with open(out, "wb") as f:
        plistlib.dump(build(), f, fmt=plistlib.FMT_BINARY)
    print("Wrote", out)
