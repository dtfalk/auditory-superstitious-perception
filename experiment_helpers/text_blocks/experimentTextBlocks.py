import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from experimenterLevers import SENTENCE_TO_IMAGINE, MIN_DB, MAX_DB, FAMILIARIZATION_PLAYS

# Instructions that are not specific to any block or condition
# =======================================================================
# =======================================================================

explanationText_1 = 'Welcome to the experiment!\n\n\
In this experiment, you will listen to a series of short, static-like audio samples. For each sample, your task is to decide whether a specific word is present in the sound.\n\n\
The word you will be listening for is \"Wall\".\n\n\
This task is intentionally very difficult. The audio samples will mostly sound like noise, and the word will never be clearly spoken or easy to hear. Many people report feeling unsure whether they ever truly hear the word they are searching for.\n\n\
Even so, people typically perform well on this task despite feeling uncertain. Feeling unsure or unconfident is normal and expected.\n\n\
Your job is not to clearly identify the word, but to listen carefully and decide whether the sound gives you the impression that the word \"Wall\" might be present.'

explanationText_2 = 'To help you think about this task, imagine overhearing someone speaking through a wall or a closed door. You can tell that a voice might be there, but the sound is muffled and buried in ambient noise. You strain to listen, trying to pick out speech, and sometimes it feels like a specific word or phrase might have been present, even though you are never sure.\n\n\
This task is similar in spirit, but the word that you are listening for will be even more difficult to discern. You will never clearly hear the word \"Wall\". Instead, you may find yourself caught between hearing and guessing, where the sound creates a vague impression rather than a definite perception.\n\n\
Many people describe this experience as a strange or superstitious feeling, where intuition, along with faint internal impressions or sensations, guides decisions more than clear evidence.\n\n\
That uneasy, in-between feeling is not a mistake or a sign that something is wrong. These subtle thoughts and impressions are a meaningful part of yourself that is quietly trying to make itself known.\n\n\
Your job is to engage with these thoughts and feelings, take them seriously, and listen carefully to what they are trying to tell you.'

explanationText_3 = f'As mentioned earlier, throughout this experiment you will always be listening for the word \"Wall\". Importantly, you will always be listening for the word \"Wall\" as it occurs within the context of this sentence:\n\n\
>>>**{SENTENCE_TO_IMAGINE}**\n\n\
- Rather than searching for an isolated word, this sentence provides the context that shapes how the word \"Wall\" would naturally sound.\n\
- You will be introduced to a specific speaker, and you will hear a recording of the speaker saying the full sentence aloud.\n\
- During the task, you are always searching for this speaker’s version of the word \"Wall\", as it would naturally occur at the end of this sentence.\n\
- The audio samples you will listen to during the task will not clearly sound like the speaker’s voice. Instead, they will sound like noise. In some of these samples, traces of the speaker’s word \"Wall\" have been hidden within the noise.\n\
- Your task is to decide whether the speaker’s \"Wall\", as spoken in the context of the sentence, seems to be present in each audio sample.'

explanationText_4 = '**What to keep in mind**\n\
    - When the word \"Wall\" is present, it always spans the entire audio sample from beginning to end.\n\
    - You should base your response on whatever impression or feeling the sound gives you, even if you are not confident.\n\n\
**Important notes**\n\
    - If you have **any** questions at any point or wish to stop, please tell the experimenter immediately.\n\
    - We know this task is challenging and truly appreciate your effort and participation.\n\
    - Please try your best. Better performance increases your chances of winning the raffle.\n\
    - If you are actively trying, it is okay to trust your intuition.\n\n\
>>>If you have **any** questions, please ask the experimenter now'

explanationText_5 = '>>>**A final note before beginning**\n\n\
Even with the sentence context and the speaker in mind, the audio samples you will hear will remain extremely noisy. You will never clearly hear the word \"Wall\" spoken in the samples.\n\n\
It is normal for many trials to feel uncertain, ambiguous, or as though nothing definite is there at all.\n\n\
That experience is expected. Doing well on this task does not require certainty or confidence, but a willingness to stay engaged and respond based on the impressions you have, even when they feel faint or unclear.\n\n\
On the next screen, you will receive instructions specific to the first block of the experiment.'

breakScreenText = 'You have now completed 1 out of 2 blocks.\n\n You have earned a break.\n\n Please let the experimenter know.\n\nWhen you are ready you will begin the next portion of the experiment.\n\n'

exitScreenText = 'Thank you for participating in this study!\n\n'\
'Please notify the experimenter that you have completed the study.\n\n'\
# =======================================================================
# =======================================================================

# Block/Condition specific instructions
# =======================================================================
# =======================================================================

# Block introduction & explanation
# =======================================================================
fullSentenceBlockInstructionsText = (
    "In this part of the experiment, on each trial you will hear a recording of the speaker saying this sentence before you make your judgement:\n\n"
    f">>>**{SENTENCE_TO_IMAGINE}**\n\n"
    "- The sentence is always the same, except that the final word is replaced by a short, static-like audio sample.\n"
    "- Your task on each trial is to decide whether the speaker’s \"Wall\", as it would naturally complete the sentence, seems to be present in that noisy audio sample.\n"
    "- Next, you will listen to the speaker say the full sentence as many times as you like.\n\n"
    "**A few important points**\n"
    "     - The audio samples themselves are not clearly spoken words. They are noisy clips that may or may not contain traces of the speaker’s \"Wall\".\n"
    "     - If the speaker’s \"Wall\" is present, it spans the entire audio sample from beginning to end.\n"
    "     - You are always judging whether the speaker’s version of \"Wall\" is present in the audio sample. You must **always** listen for the speaker's voice saying \"Wall\" and **not** your own voice or anybody else's.\n\n"
    ">>>If you have **any** questions please ask the experimenter now\n"
    ">>>Press the **spacebar** to continue"
)


imaginedSentenceBlockInstructionsText = (
    "In this part of the experiment, you will imagine the speaker saying this sentence before you make your judgment:\n\n"
    f">>>**{SENTENCE_TO_IMAGINE}**\n\n"
    "- On each trial, you will **imagine** the speaker saying the beginning of this sentence in their voice.\n"
    "- As your imagined sentence reaches the word \"Wall\", you will click \"Play Audio\" to hear a short, static-like audio sample.\n"
    "- Your task is to decide whether the speaker’s \"Wall\", as it would naturally complete the sentence, seems to be present in that noisy audio sample.\n"
    "- Next, you will listen to the speaker say the full sentence as many times as you like.\n\n"
    "**A few important points**\n"
    "     - The audio samples themselves are not clearly spoken words. They are noisy clips that may or may not contain traces of the speaker’s \"Wall\".\n"
    "     - If the speaker’s \"Wall\" is present, it spans the entire audio sample from beginning to end.\n"
    "     - You are always judging whether the speaker’s version of \"Wall\" is present in the audio sample, **not** your own imagined version.\n"
    "     - You may only **imagine** the sentence. Do **not** say the sentence out loud, move your lips or otherwise subvocalize.\n\n"
    ">>>If you have **any** questions please ask the experimenter now\n"
    ">>>Press the **spacebar** to continue."
)
# =======================================================================

# Final reminders before the first trial of the block
# =======================================================================
preTrialQuickResponseTextFullSentence = (
    ">>>**Before you begin**\n\n"
    "- On each trial, you will hear the sentence once, with the final word replaced by a noisy audio sample.\n"
    "- Each audio sample can only be heard one time. There are no replays.\n"
    "- When you are ready to respond, press **Y** if you sense that the speaker’s \"Wall\" is present, and **N** if you believe it is not.\n"
    "- Please respond quickly after hearing the stimulus.\n"
    "- On the next screen, you will be asked to respond to a single question.\n"
    "- After that, you will hear the sentence again to prepare, and the real trials will begin immediately.\n"
    "- Trust your gut feelings. It is okay to be uncertain.\n\n"
    ">>>If you have **any** questions please ask the experimenter now\n"
    ">>>Press the **spacebar** to continue"
)


preTrialQuickResponseTextImaginedSentence = (
    ">>>**Before you begin**\n\n"
    "- On **every** trial, you will **imagine** the speaker saying the sentence, then listen to a noisy audio sample.\n"
    "- Each audio sample can only be heard one time. There are no replays.\n"
    "- On every trial, imagine the sentence in the speaker’s voice and click \"Play Audio\" at the moment you would be imagining the word \"Wall\".\n"
    "- The sentence must be imagined silently. Do not say it out loud, under your breath, or move your mouth.\n"
    "- Please respond quickly after hearing the stimulus.\n"
    "- When you are ready to respond, press **Y** if you believe the speaker’s \"Wall\" is present, and **N** if you believe it is not.\n"
    "- On the next screen, you will be asked to respond to a single question.\n"
    "- After that, you will hear the sentence again to prepare, and the real trials will begin immediately.\n"
    "- Trust your gut feelings. It is okay to be uncertain.\n\n"
    ">>>If you have **any** questions please ask the experimenter now\n"
    ">>>Press the **spacebar** to continue"
)
# =======================================================================

# Instructions shown on every trial
# =======================================================================
trialInstructions_full_sentence = [
    ">>>**Main Task**\n",
    "- Click 'Play Audio' to listen to the speaker saying the sentence.",
    "- Press **Y** if you believe the speaker's \"Wall\" is hidden in the noisy audio sample.",
    "- Press **N** if you believe the speaker's \"Wall\" is **not** hidden in the noisy audio sample.",
]

trialInstructions_imagined_sentence = [
    ">>>**Main Task**\n",
    "- Silently **imagine** the speaker saying the sentence in **their** voice.", 
    "- Click 'Play Audio' when your **imagined** sentence reaches the word \"Wall\".",
    "- Press **Y** if you believe the speaker's \"Wall\" is hidden in the noisy audio sample.",
    "- Press **N** if you believe the speaker's \"Wall\" is **not** hidden in the noisy audio sample.",
]
# =======================================================================
# =======================================================================

# Pre-examples familiarization instructions (shown before block examples)
# Uses {required_plays} placeholder - must be formatted at runtime
# =======================================================================
preExamplesFamiliarizationInstructions_full_sentence = [
    ">>>**Sentence Familiarization**",
    "",
    "- You will now hear the speaker say the full sentence.",
    "- In the next screen, you will hear examples where this sentence is played, with the final word replaced by a noisy audio sample.",
    f"- You must listen to the sentence at least {FAMILIARIZATION_PLAYS} times before continuing.",
    "- You may listen to it as many additional times as you like.",
    "- Use this time to become very familiar with how the speaker sounds and how the word \"Wall\" is spoken in the context of the sentence.",
    "- You should continue listening until you feel confident you recognize the sentence and the speaker's voice.",
    "",
    ">>>Click \"Play Sentence\" to listen to the full sentence",
    ">>>Click \"Continue\" when you are ready to hear the examples"
]

preExamplesFamiliarizationInstructions_imagined_sentence = [
    ">>>**Sentence Familiarization**",
    "",
    "- You will now hear the speaker say the full sentence.",
    "- On the very next screen, you will hear examples where you must imagine the speaker saying this sentence before listening to each audio sample. Make sure that you commit this sentence to memory, as you will need to imagine it clearly and reliably on the next screen.",
    f"- You must listen to the sentence at least {FAMILIARIZATION_PLAYS} times before continuing.",
    "- You may listen to it as many additional times as you like.",
    "- Use this time to get the sentence clearly and reliably into your head in the speaker's voice.",
    "- You should continue listening until you feel confident you can imagine the speaker saying the sentence accurately, without needing to hear the audio, as you will need to imagine this sentence on the very next screen.",
    "",
    ">>>Click \"Play Sentence\" to listen to the full sentence",
    ">>>Click \"Continue\" **only** once you feel ready to use the sentence in the next screen"
]
# =======================================================================

# Target familiarization instructions (shown before main trials)
# Uses {required_plays} placeholder - must be formatted at runtime
# =======================================================================
targetFamiliarizationInstructions_full_sentence = [
    ">>>**Sentence Preparation**",
    "",
    "- You will now hear the speaker say the full sentence a limited number of times.",
    "- This sentence will be played on each trial in the next block, with the final word replaced by a noisy audio sample.",
    "- You will hear the sentence exactly {required_plays} times before continuing.",
    "- Use these listens to firmly anchor how the speaker sounds and how the word \"Wall\" is spoken in the context of the sentence.",
    "- Once these plays are complete, you will begin this portion of the experiment.",
    "- If you have **any** questions please ask the experimenter now.\n"
    "",
    ">>>Click \"Play Sentence\" to listen to the full sentence",
    ">>>Click \"Continue\" to begin the main task"
]

targetFamiliarizationInstructions_imagined_sentence = [
    ">>>**Sentence Preparation**",
    "",
    "- You will now hear the speaker say the full sentence a limited number of times.",
    "- In the next screen, you will immediately begin the task, where you must imagine the speaker saying this sentence before listening to each audio sample.",
    "- You will hear the sentence exactly {required_plays} times before continuing.",
    "- Use these listens to firmly establish the sentence in the speaker's voice so that you can reliably imagine it without hearing the audio.",
    "- Once these plays are complete, you will begin this portion of the experiment.",
    "- If you have **any** questions please ask the experimenter now.\n"
    "",
    ">>>Click \"Play Sentence\" to listen to the full sentence",
    ">>>Click \"Continue\" to begin the main task"
]
# =======================================================================

# Periodic reminder instructions (shown every N trials)
# Uses {required_plays} placeholder - must be formatted at runtime
# =======================================================================
periodicReminderInstructions_full_sentence = [
    ">>>**Sentence Reminder**",
    "",
    "- You will now hear the speaker say the full sentence again.",
    "- You will listen to the sentence {required_plays} times before continuing.",
    "- Use this as a brief reminder of how the speaker sounds and how the word \"Wall\" is spoken in the context of the sentence.",
    "",
    ">>>Click \"Play Sentence\" to listen to the full sentence",
    ">>>Click \"Continue\" to return to the task"
]

periodicReminderInstructions_imagined_sentence = [
    ">>>**Sentence Reminder**",
    "",
    "- You will now hear the speaker say the full sentence again.",
    "- You will listen to the sentence {required_plays} times before continuing.",
    "- Use this as a reminder of how the sentence sounds in the speaker's voice, so you can continue imagining it clearly before each audio sample.",
    "",
    ">>>Click \"Play Sentence\" to listen to the full sentence",
    ">>>Click \"Continue\" to return to the task"
]
# =======================================================================

# Block examples instructions
# =======================================================================
blockExamplesInstructions_imagined_sentence = (
    ">>>**Example Audio**\n\n"
    "- These are examples of the audio samples that you will hear in the task.\n"
    "- For each example, imagine the speaker saying the sentence in their voice.\n"
    "- Click the active button when your imagined sentence reaches the word \"Wall\".\n"
    "- Initially, only one example button will be active at a time. After you have listened to all examples once, all buttons will become active and you may replay any example as many times as you like.\n"
    "- Examples labeled **Wall** contain the speaker's \"Wall\" hidden in the noise. Examples labeled **No Wall** do not. The \"Actual Audio\" button plays the speaker's \"Wall\".\n"
    "- Use these examples to get a sense of how the audio samples that contain speaker's \"Wall\" differ from audio samples that do not contain the speaker's \"Wall\".\n"
    "- When you are ready, click \"Continue\" to proceed."
)

blockExamplesInstructions_full_sentence = (
    ">>>**Example Audio**\n\n"
    "- These are examples of the audio samples that you will hear in the task.\n"
    "- In each example, you will hear the speaker say the sentence, with the final word replaced by a noisy audio sample.\n"
    "- Initially, only one example button will be active at a time. After you have listened to all examples once, all buttons will become active and you may replay any example as many times as you like.\n"
    "- Examples labeled **Wall** contain the speaker's \"Wall\" hidden in the noise. Examples labeled **No Wall** do not. The \"Actual Audio\" button plays the full, original sentence spoken by the speaker.\n"
    "- Use these examples to get a sense of how the audio samples that contain speaker's \"Wall\" differ from audio samples that do not contain the speaker's \"Wall\".\n"
    "- When you are ready, click \"Continue\" to proceed."
)
# =======================================================================

# Audio level test instructions (for experimenter)
# =======================================================================
audioLevelTestInstructions = [
    "Use this screen to normalize audio levels before starting the experiment.",
    "Adjust system volume so both sounds are at comfortable levels.",
    f"The target decibel range is **{MIN_DB}** dB to **{MAX_DB}** dB.",
    "When audio levels are properly set, click 'Continue' to proceed."
]
# =======================================================================   