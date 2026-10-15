"""Plain-language sorting advice and a small transparent text helper."""
import re

CATEGORY_ORDER = ["biodegradable", "recyclable", "hazardous", "general"]
CATEGORY_INFO = {
    "biodegradable": {
        "label": "Biodegradable / compostable", "short": "Organic material that can break down naturally", "color": "green", "icon": "✳",
        "steps": ["Separate food scraps and yard trimmings from packaging.", "For a home compost pile, mix fresh scraps with dry leaves or shredded, uncoated cardboard and keep the pile aerated.", "Keep meat, dairy, oils, pet waste, and treated or painted materials out of a basic backyard pile; a suitable facility may accept some of these."],
        "note": "Soil and dirt are not automatically compostable. Keep them out of a food-scrap compost pile unless the composting guidance for your system says otherwise.",
        "links": [("EPA: Composting at home", "https://www.epa.gov/recycle/composting-home")],
    },
    "recyclable": {
        "label": "Recyclable material", "short": "A material that may be recovered or reused", "color": "blue", "icon": "↻",
        "steps": ["If it is clean and usable, consider reusing it or offering it to someone who can use it.", "Separate common material types: paper and cardboard, glass containers, metal cans, and plastic packaging.", "Keep food and liquid out, and separate parts made from different materials when practical."],
        "note": "This identifies the material; it does not promise that every collection program accepts it. Broken glass and mixed-material items need extra care.",
        "links": [("EPA: Common recyclables", "https://www.epa.gov/recycle/how-do-i-recycle-common-recyclables"), ("Give usable items away: Freecycle", "https://www.freecycle.org/"), ("Give usable items away: Buy Nothing", "https://buynothingproject.org/")],
    },
    "hazardous": {
        "label": "Hazardous / special handling", "short": "May need a separate collection or take-back route", "color": "amber", "icon": "!",
        "steps": ["Keep the item in its original, closed container when safe to do so; do not mix it with other products.", "Do not pour chemicals, oil, or paint into a drain, onto the ground, or into storm water.", "Look for an appropriate household hazardous-waste, battery, electronics, or medicine take-back service. Follow the product label and collection service instructions."],
        "note": "A photo may not reveal contents or condition. If a container is leaking, damaged, unlabeled, or giving off fumes, do not handle it; seek qualified local help.",
        "links": [("EPA: Household hazardous waste", "https://www.epa.gov/hw/household-hazardous-waste-hhw"), ("EPA: Used batteries", "https://www.epa.gov/recycle/used-lithium-ion-batteries")],
    },
    "general": {
        "label": "General waste / check first", "short": "Not clearly compostable or recyclable from this information", "color": "slate", "icon": "○",
        "steps": ["Check whether the item can be repaired, reused, or donated before discarding it.", "If it is a clean, single material, check whether it has a recycling option.", "If it contains chemicals, batteries, electronics, or a medicine, use the special-handling guidance instead of placing it in general waste."],
        "note": "Some items combine materials or need handling that cannot be determined from a photo. Use the item label or ask a waste professional when in doubt.",
        "links": [("EPA: Reduce, reuse, recycle", "https://www.epa.gov/recycle"), ("Freecycle", "https://www.freecycle.org/"), ("Buy Nothing", "https://buynothingproject.org/")],
    },
}

ITEM_STEPS = {
    "food scraps": ["Keep scraps separate from wrappers and other packaging.", "Compost them in a suitable home or community food-waste system; add dry leaves or shredded uncoated cardboard to balance wet scraps.", "Check your compost system’s rules before adding meat, dairy, oil, or cooked food."],
    "garden waste": ["Keep leaves and plant trimmings separate from plastic pots, soil bags, and treated wood.", "Compost or mulch clean plant material where permitted, or use a garden-waste collection service.", "Do not burn treated or unknown plant material."],
    "paper or cardboard": ["Keep it dry and free of food or grease; flatten cardboard to save space.", "Remove plastic wrapping, tape, and other obvious non-paper parts when practical.", "Place it in a paper/cardboard collection accepted by your local service, or reuse clean boxes."],
    "plastic": ["Empty and scrape out leftover contents; rinse only if your local program asks for clean containers.", "Check the resin/type and shape rules for your local program because not all plastics are accepted.", "Keep plastic film and bags separate unless your collection explicitly accepts them."],
    "glass": ["Reuse a clean, intact container when practical; otherwise check local glass collection rules.", "Do not put broken glass into a recycling bin unless the local service explicitly allows it; wrap and label it for safe handling.", "Keep drinking glasses, mirrors, ceramics, and window glass separate from bottle/jar glass."],
    "metal": ["Empty the container and keep it separate from hazardous contents.", "Rinse food residue if required by your local program, then place accepted cans in metal recycling.", "Do not treat paint, chemical, or pressurized containers as ordinary scrap metal."],
    "battery": ["Do not place loose batteries in household recycling or general waste where a separate battery service is available.", "Tape exposed terminals on lithium or 9-volt batteries and take them to a battery collection point.", "If a battery is swollen, hot, leaking, or damaged, avoid handling it and seek local hazardous-waste guidance."],
    "electronic waste": ["Back up and erase personal data when possible; remove batteries only if designed to be removable.", "Use an electronics take-back, repair, donation, or certified e-waste collection service.", "Do not dismantle devices or put them in ordinary recycling."],
    "medicine": ["Keep medicines in their packaging and out of sinks, toilets, and ordinary recycling.", "Use a pharmacy or authorized medicine take-back service when available.", "Follow the product label and local health guidance for medicines with no take-back option."],
    "paint or chemicals": ["Keep the product labeled and sealed if safe; never mix it with other chemicals.", "Do not pour paint, oil, or chemicals into drains, onto soil, or into storm water.", "Use the product label and a household hazardous-waste collection service for the correct route."],
    "clothes": ["If clean and wearable, repair, donate, swap, or resell them before discarding.", "For worn-out fabric, look for a textile take-back or reuse program; textile recycling rules vary by location.", "Keep wet, moldy, or chemically contaminated fabric out of donation bins."],
    "shoes": ["If still usable, clean them and donate, repair, or resell them as a pair.", "If damaged beyond use, check for a shoe take-back or textile recovery service.", "Do not assume shoes belong in ordinary curbside recycling; mixed materials are usually not accepted there."],
}

FOLDER_TO_CATEGORY = {
    "food_scraps": "biodegradable", "yard_waste": "biodegradable",
    "other_organic": "biodegradable",
    "paper_cardboard": "recyclable", "paper": "recyclable", "plastic": "recyclable", "metal": "recyclable", "glass": "recyclable",
    "batteries": "hazardous", "paint_chemicals": "hazardous", "medicine": "hazardous", "electronics": "hazardous",
    "general_waste": "general", "textile": "general",
}
FOLDER_TO_ITEM = {
    "food_scraps": "food scraps", "yard_waste": "garden waste", "other_organic": "other organic waste",
    "paper_cardboard": "paper", "paper": "paper", "plastic": "plastic", "metal": "metal", "glass": "glass",
    "batteries": "battery", "paint_chemicals": "paint or chemicals", "medicine": "medicine",
    "electronics": "electronic waste", "general_waste": "general trash", "textile": "textile",
}

# The dataset's prepared folder names are kept here too, so every train label
# has an explicit meaning in the app (including the dataset's paper_cardboard).
FOLDER_TO_CATEGORY.update({"paper_cardboard": "recyclable", "yard_waste": "biodegradable"})
FOLDER_TO_ITEM.update({"paper_cardboard": "paper or cardboard", "yard_waste": "garden waste"})
FOLDER_TO_CATEGORY.update({
    "battery": "hazardous", "biological": "biodegradable", "brown-glass": "recyclable",
    "cardboard": "recyclable", "clothes": "general", "green-glass": "recyclable",
    "shoes": "general", "trash": "general", "white-glass": "recyclable",
})
FOLDER_TO_ITEM.update({
    "battery": "battery", "biological": "organic waste", "brown-glass": "brown glass",
    "cardboard": "cardboard", "clothes": "clothes", "green-glass": "green glass",
    "shoes": "shoes", "trash": "general waste", "white-glass": "clear glass",
})
KEYWORDS = {
    "hazardous": ["battery", "batteries", "paint", "oil paint", "chemical", "cleaner", "medicine", "medication", "pill", "pills", "pesticide", "solvent", "electronic", "phone", "laptop", "charger", "e-waste"],
    "biodegradable": ["food", "scrap", "banana peel", "peel", "fruit", "vegetable", "coffee grounds", "leaves", "leaf", "grass", "garden waste", "yard waste", "compost", "biological waste", "organic waste"],
    "recyclable": ["cardboard", "paper", "plastic", "bottle", "glass", "aluminum", "aluminium", "metal", "tin", "tin can", "metal can", "soda can", "food can"],
    "general": ["diaper", "nappy", "wrapper", "styrofoam", "foam", "dust", "dirt", "soil", "ceramic", "broken mirror", "mixed material", "clothes", "clothing", "shoes", "footwear", "sneakers"],
}

def describe_text(text: str) -> dict:
    """Return a conservative category guess from explicit item words."""
    value = " ".join(text.lower().strip().split())
    if not value:
        return {"status": "unknown", "category": None, "item": "", "confidence": None}
    matches = [
        (category, word)
        for category, words in KEYWORDS.items()
        for word in words
        if re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", value)
    ]
    if not matches:
        return {"status": "unknown", "category": None, "item": value[:80], "confidence": None}
    matches.sort(key=lambda pair: (pair[0] != "hazardous", -len(pair[1])))
    category, matched = matches[0]
    return {"status": "ready", "category": category, "item": value[:80], "confidence": None, "matched_word": matched}
