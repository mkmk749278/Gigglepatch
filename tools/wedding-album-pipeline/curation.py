"""STAGE 5c: authored visual curation.

These scores come from direct visual inspection of every one of the 599 cluster
representatives (see album/previews/review/*.jpg), not from an automated
classifier. Technical measurements from s02/s04 are combined with these in
s06_select.py using the weighting in the brief.

Scores are 1-10.  emo = emotional value, comp = composition,
story = storytelling contribution, suit = album suitability.

role:  hero    -> earns a full page (usually full bleed)
       spread  -> earns a double-page spread
       portrait-> close-up, gets portrait treatment
       support -> works inside a multi-photo editorial page
       detail  -> hands / jewellery / decor / objects
       cover / closing -> book furniture
"""

CHAPTERS = [
    ("home_blessings", "Blessings at Home", "8 June 2020"),
    ("turmeric", "The Turmeric Rite", "8 June 2020"),
    ("the_bride", "The Bride", "12 June 2020"),
    ("the_groom", "The Groom", "12 June 2020"),
    ("rituals", "The Vows", "12 June 2020"),
    ("talambralu", "A Shower of Rice", "12 June 2020"),
    ("blessings", "Blessings", "12 June 2020"),
    ("the_feast", "The Feast", "12 June 2020"),
    ("reception", "The Celebration", "12 June 2020"),
    ("couple_portraits", "Just the Two", "studio session"),
    ("days_after", "The Days After", "17 June 2020"),
]

COVER = {"file": "DSC_0700.JPG", "note": "couple seated at the mandap, symmetrical, clean lower third for type"}
CLOSING = {"file": "DSC_0922.JPG", "note": "quiet closing portrait, warm evening light"}

# file, chapter, category, role, emo, comp, story, suit, note
SELECTION = [
    # ---------------------------------------------- 1. Blessings at Home (Jun 8)
    ("DSC_0267.JPG", "home_blessings", "detail", "detail", 5, 7, 8, 7, "puja cloth, framed portrait and offerings laid out - opens the story quietly"),
    ("DSC_0270.JPG", "home_blessings", "ritual", "support", 8, 7, 9, 8, "elder bent over the offerings, hands at his face"),
    ("DSC_0287.JPG", "home_blessings", "ritual", "hero", 8, 8, 8, 8, "groom with palms joined at the doorway, strong side light"),
    ("DSC_0295.JPG", "home_blessings", "groom", "portrait", 8, 7, 7, 8, "groom praying, vertical, mirror behind"),
    ("DSC_0278.JPG", "home_blessings", "family", "portrait", 8, 7, 6, 7, "young boy in dhoti and blue shirt, direct gaze"),
    ("DSC_0304.JPG", "home_blessings", "family", "portrait", 9, 7, 6, 8, "boy grinning against brick - genuine warmth"),
    ("DSC_0299.JPG", "home_blessings", "detail", "detail", 4, 7, 7, 6, "rangoli, brass pot and coconut on the courtyard stone"),

    # ---------------------------------------------- 2. Turmeric (Jun 8)
    ("DSC_0307.JPG", "turmeric", "ritual", "support", 7, 6, 8, 7, "groom seated on the low stool before the rite begins"),
    ("DSC_0359.JPG", "turmeric", "ritual", "hero", 8, 7, 8, 8, "relative tipping the plate over him, best frame of the sequence"),
    ("DSC_0343.JPG", "turmeric", "ritual", "support", 7, 7, 7, 7, "women crowding in with the turmeric plate"),
    ("DSC_0391.JPG", "turmeric", "ritual", "support", 8, 6, 9, 8, "groom coated head to chest in turmeric - the payoff of the sequence"),

    # ---------------------------------------------- 3. The Bride (Jun 12 am)
    ("DSC_0398.JPG", "the_bride", "venue", "support", 4, 7, 8, 7, "the house at 06:23, chairs set out, day not yet begun"),
    ("DSC_0400.JPG", "the_bride", "celebration", "support", 7, 7, 8, 7, "party carrying the decorated pot under an umbrella"),
    ("DSC_0401.JPG", "the_bride", "emotional", "support", 9, 7, 9, 9, "an older woman's hands settling the bride's hair"),
    ("DSC_0410.JPG", "the_bride", "bride", "hero", 9, 8, 9, 10, "the bride standing in red and gold - best bride frame in the set"),
    ("DSC_0419.JPG", "the_bride", "bride", "portrait", 9, 8, 8, 9, "bride close-up, jasmine in her hair"),
    ("DSC_0420.JPG", "the_bride", "bride", "portrait", 8, 8, 7, 8, "second close-up, softer expression"),
    ("DSC_0425.JPG", "the_bride", "bride", "support", 7, 7, 7, 8, "seated indoors, gold saree catching the window light"),
    ("DSC_0417.JPG", "the_bride", "candid", "support", 8, 7, 9, 8, "walking the dirt lane with her family, village behind"),
    ("DSC_0404.JPG", "the_bride", "family", "support", 8, 6, 8, 7, "bride with women of the family crowding round"),

    # ---------------------------------------------- 4. The Groom (Jun 12)
    ("DSC_0477.JPG", "the_groom", "venue", "hero", 5, 9, 9, 9, "the mandap dressed in yellow and pink - the stage for everything after"),
    ("DSC_0479.JPG", "the_groom", "detail", "detail", 5, 8, 7, 7, "garlanded deities in the shrine"),
    ("DSC_0488.JPG", "the_groom", "groom", "hero", 8, 8, 9, 10, "groom full length in cream sherwani and red dhoti"),
    ("DSC_0494.JPG", "the_groom", "groom", "portrait", 7, 8, 7, 8, "standing portrait, hands easy at his sides"),
    ("DSC_0496.JPG", "the_groom", "groom", "support", 7, 7, 7, 8, "same set-up, weight shifted, more relaxed"),
    ("DSC_0500.JPG", "the_groom", "family", "hero", 8, 8, 9, 9, "groom with his family indoors - technically the cleanest group frame"),
    ("DSC_0466.JPG", "the_groom", "candid", "portrait", 9, 7, 6, 8, "toddler in a striped tee, completely unimpressed"),

    # ---------------------------------------------- 5. The Vows (Jun 12 10:30-11:35)
    ("DSC_0516.JPG", "rituals", "detail", "detail", 7, 8, 8, 8, "henna hands cupping a betel leaf and turmeric"),
    ("DSC_0517.JPG", "rituals", "detail", "detail", 6, 8, 7, 7, "second hands frame, bangles and ring"),
    ("DSC_0522.JPG", "rituals", "ritual", "hero", 9, 8, 9, 9, "jeelakarra-bellam - paste pressed to his head, her bangled arm across frame"),
    ("DSC_0526.JPG", "rituals", "ritual", "support", 8, 8, 8, 8, "the same rite a beat later, both hands raised"),
    ("DSC_0532.JPG", "rituals", "ritual", "support", 7, 7, 8, 8, "priest leaning in over the couple"),
    ("DSC_0541.JPG", "rituals", "ritual", "hero", 8, 9, 9, 9, "wide of the pair at the vessel; kept as a full page - a 2.6:1 spread crop of a 3:2 frame left mostly floor mat"),
    ("DSC_0549.JPG", "rituals", "couple", "hero", 8, 9, 9, 9, "couple seated together at the ritual plate, beautifully balanced"),
    ("DSC_0587.JPG", "rituals", "detail", "detail", 6, 8, 8, 7, "toe-ring being fastened - small, culturally central"),
    ("DSC_0543.JPG", "rituals", "detail", "detail", 6, 7, 8, 6, "feet and silver rings, turmeric-stained cloth"),
    ("DSC_0515.JPG", "rituals", "bride", "portrait", 9, 8, 7, 9, "bride close-up, gold headpiece, eyes down"),
    ("DSC_0546.JPG", "rituals", "bride", "portrait", 9, 8, 7, 9, "bride with palms joined - the quietest frame of the day"),
    ("DSC_0573.JPG", "rituals", "groom", "portrait", 8, 8, 8, 9, "groom in the red and white turban, close"),
    ("DSC_0575.JPG", "rituals", "bride", "portrait", 8, 8, 7, 8, "bride standing in cream and gold before the vows"),
    ("DSC_0597.JPG", "rituals", "ritual", "support", 8, 7, 8, 8, "groom bent low over her, tying"),
    ("DSC_0600.JPG", "rituals", "ritual", "hero", 10, 9, 10, 10, "the mangalsutra being tied - the single most important moment, and the sharpest frame of it"),
    ("DSC_0601.JPG", "rituals", "bride", "portrait", 9, 8, 8, 9, "bride just after, half-smiling"),
    ("DSC_0602.JPG", "rituals", "bride", "portrait", 9, 8, 7, 8, "same moment, chin lifted"),
    ("DSC_0610.JPG", "rituals", "groom", "portrait", 8, 7, 7, 8, "groom in turban, pleased with himself"),
    ("DSC_0595.JPG", "rituals", "detail", "detail", 6, 8, 7, 7, "four hands over the ritual plate"),

    # ---------------------------------------------- 6. Talambralu (11:44-11:50)
    ("DSC_0648.JPG", "talambralu", "ritual", "spread", 10, 9, 10, 10, "rice pouring between them - highest technical score in the whole collection"),
    ("DSC_0642.JPG", "talambralu", "ritual", "hero", 9, 9, 9, 10, "both arms up, rice falling, faces bright"),
    ("DSC_0649.JPG", "talambralu", "ritual", "support", 9, 8, 8, 9, "her turn, laughing"),
    ("DSC_0653.JPG", "talambralu", "ritual", "support", 9, 8, 8, 9, "his hands over her head, mid-pour"),
    ("DSC_0655.JPG", "talambralu", "ritual", "support", 8, 8, 8, 8, "the vessel tipping, grains in the air"),
    ("DSC_0646.JPG", "talambralu", "bride", "portrait", 10, 8, 9, 10, "bride with rice and flowers heaped in her hair - the album's best portrait"),
    ("DSC_0645.JPG", "talambralu", "groom", "portrait", 9, 8, 8, 9, "groom taking his share, eyes shut"),
    ("DSC_0658.JPG", "talambralu", "ritual", "support", 8, 8, 8, 8, "quieter beat, both hands working"),

    # ---------------------------------------------- 7. Blessings (11:30-12:15)
    ("DSC_0618.JPG", "blessings", "family", "support", 8, 7, 8, 8, "guests stepping up to the seated couple"),
    ("DSC_0553.JPG", "blessings", "family", "support", 8, 7, 9, 8, "elders' hands on their heads"),
    ("DSC_0673.JPG", "blessings", "ritual", "support", 7, 7, 8, 7, "the priest between them at the mandap"),
    ("DSC_0682.JPG", "blessings", "celebration", "hero", 10, 8, 9, 9, "both arms thrown up together - pure release"),
    ("DSC_0699.JPG", "blessings", "couple", "hero", 8, 9, 9, 9, "the two of them garlanded on the flower-strewn floor"),
    ("DSC_0700.JPG", "blessings", "couple", "cover", 9, 9, 9, 10, "couple seated at the mandap, symmetrical, clean lower third for type"),
    ("DSC_0703.JPG", "blessings", "bride", "portrait", 9, 8, 8, 9, "bride close, garlanded, calm"),
    ("DSC_0704.JPG", "blessings", "groom", "portrait", 8, 8, 7, 8, "groom close, garland and turban"),
    ("DSC_0690.JPG", "blessings", "bride", "portrait", 8, 8, 8, 8, "bride alone, full length, gold and cream"),
    ("DSC_0694.JPG", "blessings", "groom", "portrait", 8, 8, 8, 8, "groom alone against the mandap arch"),
    ("DSC_0707.JPG", "blessings", "family", "support", 8, 7, 8, 8, "couple ringed by family on the flowers"),

    # ---------------------------------------------- 8. The Feast (12:21)
    ("DSC_0715.JPG", "the_feast", "celebration", "hero", 7, 9, 10, 9, "the long table running away into the field - the whole village eating; kept as a full page because a 2.6:1 spread crop left one half as empty ground"),
    ("DSC_0719.JPG", "the_feast", "celebration", "support", 7, 8, 9, 8, "further down the same table, plates full"),

    # ---------------------------------------------- 9. The Celebration (13:59-16:10)
    ("DSC_0819.JPG", "reception", "celebration", "hero", 10, 8, 9, 9, "arms up again on the reception stage, confetti light"),
    ("DSC_0818.JPG", "reception", "celebration", "support", 9, 8, 8, 8, "the beat before, both mid-laugh"),
    ("DSC_0805.JPG", "reception", "family", "support", 8, 7, 8, 8, "greeting guests across the table"),
    ("DSC_0804.JPG", "reception", "family", "support", 8, 7, 8, 8, "children pressed in around them"),
    ("DSC_0810.JPG", "reception", "emotional", "support", 9, 7, 8, 8, "a baby handed across for a blessing"),
    ("DSC_0780.JPG", "reception", "bride", "portrait", 8, 8, 7, 8, "reception bride close-up, changed saree"),
    ("DSC_0816.JPG", "reception", "groom", "portrait", 7, 7, 7, 7, "groom in the navy suit and red bow tie"),
    ("DSC_0800.JPG", "reception", "detail", "detail", 6, 7, 7, 7, "the iced cake waiting to be cut"),
    ("DSC_0757.JPG", "reception", "couple", "support", 8, 7, 8, 8, "the two of them settled on the reception seat"),
    ("DSC_0887.JPG", "reception", "family", "support", 7, 7, 8, 7, "outdoor group under the awning, late light"),
    ("DSC_0754.JPG", "reception", "family", "portrait", 8, 8, 7, 8, "young relative in a yellow half-saree, arms folded"),

    # ---------------------------------------------- 10. Studio couple portraits
    ("DSC_0047.JPG", "couple_portraits", "couple", "portrait", 9, 8, 8, 9, "her hand on his chest, grey suit and orange silk"),
    ("DSC_0045.JPG", "couple_portraits", "couple", "support", 8, 7, 7, 8, "full length, formal, side by side"),
    ("DSC_0057.JPG", "couple_portraits", "couple", "portrait", 8, 8, 7, 8, "white kurta against the blue backdrop"),

    # ---------------------------------------------- 11. The Days After (Jun 17)
    ("DSC_0874.JPG", "days_after", "emotional", "portrait", 10, 8, 7, 9, "baby girl in green and pink, wide-eyed - impossible to leave out"),
    ("DSC_0869.JPG", "days_after", "emotional", "portrait", 9, 7, 6, 8, "same child, fingers in her mouth"),
    ("DSC_0876.JPG", "days_after", "emotional", "support", 9, 7, 6, 8, "sat in the orange plastic chair, feet not reaching"),
    ("DSC_0893.JPG", "days_after", "detail", "detail", 8, 7, 9, 8, "a framed portrait on the wall of the house - the family's own memory, kept"),
    ("DSC_0895.JPG", "days_after", "family", "portrait", 8, 7, 8, 8, "woman in pink and green kneeling on the rangoli with a child"),
    ("DSC_0915.JPG", "days_after", "ritual", "support", 7, 7, 8, 7, "the evening blessing line, plate passing hands"),
    ("DSC_0897.JPG", "days_after", "ritual", "support", 7, 7, 8, 7, "chalk rangoli underfoot, guests waiting their turn"),
    ("DSC_0922.JPG", "days_after", "bride", "closing", 9, 8, 8, 9, "quiet closing portrait in the orange and green silk, warm evening light"),
]

WEIGHTS = {"technical": 0.20, "composition": 0.20, "emotion": 0.25,
           "storytelling": 0.20, "uniqueness": 0.10, "suitability": 0.05}

# Manual reframing hints, added after inspecting these frames at full resolution
# (album/previews/hero_check.jpg). Fractions of the ORIGINAL frame, applied
# before layout: (x0, y0, x1, y1). These only ever crop inward.
CROP_HINTS = {
    # standing groom / seated bride, with a quarter of the frame empty floor mat
    # and a bystander clipped at the left edge
    "DSC_0600.JPG": (0.05, 0.015, 1.00, 0.80),
    # busy floral curtain; tighten the sides and keep her centred
    "DSC_0410.JPG": (0.09, 0.015, 0.93, 1.00),
    # trim the bright over-exposed wall on the right
    "DSC_0488.JPG": (0.02, 0.00, 0.90, 1.00),
    # drop a little foreground mat, keeping enough width that the full-bleed
    # placement still downsamples rather than enlarges
    "DSC_0642.JPG": (0.00, 0.00, 1.00, 0.95),
}
