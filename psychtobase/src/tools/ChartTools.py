import logging

from .. import Constants, files, Utils
from ..Paths import Paths

from copy import deepcopy
from pathlib import Path

class ChartObject:

    # 🔥 MAPA DE NOTE TYPES (EDITA AQUÍ SI QUIERES MÁS)
    NOTE_TYPE_MAP = {
        "Hurt Note": "corrupt",
        "Poison Note": "poison",
        "GF Sing": "gf",
        "No Animation": "no_anim",
        "Alt Animation": None  # se maneja como evento
    }

    def __init__(self, path: str, output:str, EventsYesOrNO:bool) -> None:
        self.songPath = Path(path)
        self.savePath = Path(output)

        self.songFile = self.songPath.name
        self.songName = self.songFile.replace("-", " ")

        self.startingBpm = 0
        self.sections = []

        self.metadata:dict = deepcopy(Constants.BASE_CHART_METADATA)
        self.charts:dict = {}
        self.difficulties:list = []

        self.chart:dict = deepcopy(Constants.BASE_CHART)
        self.chart["events"] = []

        self.shouldConvertEvents = EventsYesOrNO

        self.initCharts()

        try:
            self.setMetadata()
        except:
            logging.error('Failed to set metadata')

        logging.info(f"Chart for {self.metadata.get('songName')} was created!")

    # ----------------------------
    # (TODO LO DEMÁS IGUAL)
    # ----------------------------

    def convert(self):
        logging.info(f"Chart conversion for {self.metadata.get('songName')} started!")

        prevMustHit = self.sampleChart["notes"][0].get("mustHitSection", True)
        prevTime = 0

        events = self.chart["events"]
        events.append(Utils.focusCamera(0, prevMustHit))

        existing_events = set()

        for i, (diff, cChart) in enumerate(self.charts.items()):
            self.chart["scrollSpeed"][diff] = cChart.get("speed")
            notes = self.chart["notes"][diff] = []

            steps = 0
            prev_notes = set()
            total_duplicates = 0

            for section in cChart.get("notes"):
                mustHit = section.get("mustHitSection", True)
                isDuet = False

                for note in section.get("sectionNotes"):
                    strumTime = note[0]
                    noteData = note[1]
                    length = note[2]

                    note_kind = ""  # 🔥 NUEVO

                    if noteData < 0 and self.shouldConvertEvents:
                        continue

                    if not mustHit:
                        noteData = (noteData + 4) % 8
                        if not isDuet and noteData < 4:
                            isDuet = True

                    # ❌ duplicados
                    is_duplicate = any(
                        abs(existing_note[0] - strumTime) < 1 and existing_note[1] == noteData
                        for existing_note in prev_notes
                    )

                    if is_duplicate:
                        total_duplicates += 1
                        continue

                    prev_notes.add((strumTime, noteData))

                    # 🔥 NOTE TYPES (NUEVO)
                    if len(note) > 3:
                        note_type = note[3]

                        # ALT ANIM (se queda como evento)
                        if note_type == "Alt Animation":
                            target = "player" if noteData in range(4) else "opponent"

                            if noteData in [0, 4]:
                                anim = "singLEFT-alt"
                            elif noteData in [1, 5]:
                                anim = "singDOWN-alt"
                            elif noteData in [2, 6]:
                                anim = "singUP-alt"
                            else:
                                anim = "singRIGHT-alt"

                            play_animation = (strumTime, target, anim)

                            if play_animation not in existing_events:
                                events.append(Utils.playAnimation(strumTime, target, anim, True))
                                existing_events.add(play_animation)

                        # 🔥 OTROS NOTE TYPES → "k"
                        elif note_type in self.NOTE_TYPE_MAP:
                            mapped = self.NOTE_TYPE_MAP[note_type]
                            if mapped:
                                note_kind = mapped

                        else:
                            # fallback (por si quieres mantener el nombre original)
                            note_kind = note_type.lower().replace(" ", "_")

                    # 🔥 AQUI SE GUARDA CON "k"
                    notes.append(Utils.note(noteData, length, strumTime, note_kind))

                # ----------------------------
                # RESTO IGUAL (secciones)
                # ----------------------------
                if i == 0:
                    lengthInSteps = section.get("lengthInSteps", section.get("sectionBeats", 4) * 4)
                    sectionBeats = section.get("sectionBeats", lengthInSteps / 4)

                    bpm = section.get('bpm', self.startingBpm)
                    changeBPM = section.get('changeBPM', False)

                    self.sections.append({
                        'mustHitSection': mustHit,
                        'isDuet': isDuet,
                        'lengthInSteps': lengthInSteps,
                        'bpm': bpm,
                        'changeBPM': changeBPM
                    })

                    if (prevMustHit != mustHit):
                        events.append(Utils.focusCamera(prevTime + steps * self.stepCrochet, mustHit))
                        prevMustHit = mustHit

                    steps += lengthInSteps

                    if changeBPM:
                        prevTime += steps * self.stepCrochet
                        self.metadata["timeChanges"].append(
                            Utils.timeChange(prevTime, bpm, sectionBeats, sectionBeats, 0, [sectionBeats]*4)
                        )
                        self.stepCrochet = 15000 / bpm
                        steps = 0

            if total_duplicates > 0:
                logging.warn(f"Removed {total_duplicates} duplicate notes in '{diff}'")

        logging.info(f"Chart conversion for {self.metadata.get('songName')} was completed!")
