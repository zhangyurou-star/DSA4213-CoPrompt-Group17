"""Freshly authored constrained-writing data; offline only, no experimental API."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
import hashlib, importlib.util, json, re, sys
ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT.parents[1]
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location('fresh_validator', ORIGINAL/'tools/validate_design.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
validator.ROOT = ROOT
from coprompt.scoring import score_output, count_words, normalize_text
PLAN = json.loads((ROOT/'work/writing_family_plan.json').read_text())
ALLOCATION = json.loads((ROOT/'data/allocation_plan.json').read_text())
FIELDS = json.loads((ROOT/'data/public/field_catalog.json').read_text())['domains']['constrained_writing']['field_order']
DATA = []
def add(audience, tone, bounds, literals, facts, witness):
    DATA.append(dict(audience=audience, tone=tone, bounds=bounds, literals=literals, facts=facts, witness=witness))

# Family plan was saved before any entries below were authored. Every fact is invented.
add('players who know the basic rules', 'patient and impartial', (55,85),
['Amber Gate', 'one lantern', 'the bridge remains closed'],
'In Amber Gate, a player spends one lantern to inspect a bridge. Inspection reveals its symbol but does not open it: the bridge remains closed. A separate key action opens it.',
'''In Amber Gate, spending one lantern lets you inspect the bridge and see its symbol. It does not grant passage, so the bridge remains closed after inspection. Opening it requires the separate key action. If a player has already moved across after inspecting, return that piece to its previous space and continue from there. Treat the lantern as spent because the inspection still provided information.''')
add('first-time machine users', 'clear and reassuring', (50,80),
['blue token', 'one paper kite', 'return slot'],
'A blue token buys one paper kite from the fictional machine. Insert it in the upper opening. If no kite appears, retrieve the token from the return slot; do not insert a second token.',
'''Your blue token pays for one paper kite. Place it in the upper opening, then wait until the kite tray stops moving before taking your kite. If the tray stays empty, check the return slot for your token. Keep that token and try again only after the machine has reset. Adding another token will not make the first request finish sooner.''')
add('readers aged ten and above', 'gentle and reflective', (60,90),
['a borrowed shadow', 'the well', 'share the shade'],
'The fable must feature a lizard carrying a borrowed shadow, a dispute at the well, and the closing lesson share the shade.',
'''A lizard carried a borrowed shadow across the burning village square. At the well, a beetle asked to rest beneath it. The lizard refused, saying borrowed things could not be shared. Then a cloud crossed the sun, and both creatures stood comfortably in its shadow. The lizard looked up, embarrassed that the cloud had asked for nothing. When the sun returned, he invited the beetle closer: share the shade.''')
add('a fictional nursery naming committee', 'thoughtful and descriptive', (50,80),
['Copper Lantern', 'bronze petals', 'evening bloom'],
'Propose Copper Lantern as the cultivar name. Its invented traits are bronze petals and an evening bloom that opens after the surrounding flowers close.',
'''Copper Lantern connects the plant's bronze petals with the warm light of a lamp. Its evening bloom strengthens that connection: the flower opens when the surrounding beds are already closing for the night. The name gives visitors a useful picture without requiring botanical knowledge. It also distinguishes this cultivar by color and daily rhythm, two features they can notice for themselves.''')
add('an illustrator accepting a private commission', 'precise and imaginative', (65,95),
['Glass Marsh', 'three floating islands', 'no compass rose'],
'The commissioned map depicts Glass Marsh with three floating islands connected by dotted migration paths. Water is shown as uncolored paper. Include no compass rose because direction changes in this invented world.',
'''Please depict Glass Marsh as a shifting landscape centered on three floating islands. Connect the islands with dotted migration paths rather than permanent bridges, and leave the water as uncolored paper so the land shapes remain distinct. Use small reed marks to establish the marsh setting. Include no compass rose: direction changes in this world, and a fixed north would misrepresent how its travelers find their way.''')
add('solvers who want help without an immediate reveal', 'encouraging and restrained', (45,75),
['First hint', 'Second hint', 'Answer: echo'],
'Write three increasingly revealing hints for echo. The first mentions returning, the second mentions sound, and the final line includes Answer: echo.',
'''First hint: Think of something that returns without walking back toward you. Pause here if that is enough to try another answer. Second hint: It belongs to sound, and an empty hall can make it easier to notice. Final hint: Your voice seems to reply to itself after meeting a distant surface. Answer: echo.''')
add('translators working on the invented Riverglass story', 'editorial and practical', (55,85),
['moonwell', 'do not translate', 'glossary entry'],
'The invented device name moonwell is fixed across languages: do not translate it. Its ordinary description can be localized. Any alternate spelling must be recorded in a glossary entry before drafting.',
'''Keep moonwell unchanged whenever it names the story's device; do not translate that term into a descriptive substitute. The surrounding explanation of how the device works may be localized for natural reading. If a manuscript introduces another spelling, record it in a glossary entry before drafting that passage. This keeps the name stable while allowing the prose around it to sound natural in each language.''')
add('home sewists using the invented pattern', 'direct and orderly', (60,90),
['folded edge', 'two cuffs', 'leave the center strip'],
'The mock pattern places the body against the folded edge and two cuffs beside the outer edge. Keep the printed arrows parallel. Instruct the reader to leave the center strip for the tie.',
'''Set the body piece against the folded edge of the fabric, then place the two cuffs near the outer edge. Keep every printed arrow parallel before you mark any cutting lines. Check the space between the pieces and leave the center strip for the tie. Once the arrangement is settled, trace all pieces first; cutting immediately can make it harder to notice that the reserved strip has become too narrow.''')
add('shoppers reading a fictional craft label', 'warm and understated', (50,80),
['Harbor Thread', 'cedar boxes', 'a spiral stamp'],
'Harbor Thread began as an imaginary soap workshop using empty cedar boxes as molds. Its maker marks every bar with a spiral stamp to recall the curled wood shavings on the first workbench.',
'''Harbor Thread began on a small workbench surrounded by cedar boxes and curled wood shavings. The empty boxes became the workshop's first soap molds, giving each batch a simple, square shape. Today, a spiral stamp remembers those shavings and the experiments that started the craft. The mark is a small piece of the workshop's story, pressed into every bar before it leaves the bench.''')
add('mission analysts reading fictional telemetry prose', 'observant and unemotional', (55,85),
['Probe Lark', 'seven pulses', 'no surface image'],
'Probe Lark receives seven pulses from below an icy ridge, but obtains no surface image because its camera shutter remains closed. End with a plan to repeat the listening pass.',
'''Probe Lark crossed the icy ridge and recorded seven pulses from beneath it. The spacing was regular enough to distinguish the sequence from the surrounding noise, but the source remains unidentified. There is no surface image: the camera shutter stayed closed throughout the pass. The next observation will repeat the listening route at the same height so the timing and strength of the signal can be compared.''')
add('residents of the invented Kingdom of Reeds', 'formal and ceremonial', (55,85),
['Day of Open Doors', 'every courtyard', 'one shared song'],
'The proclamation establishes the Day of Open Doors. On that fictional day, every courtyard receives a guest, and the ceremony ends with one shared song instead of a royal speech.',
'''Hear the declaration of the Kingdom of Reeds: this shall be the Day of Open Doors. Let every courtyard receive a guest, whether that guest arrives from the next street or beyond the farthest field. Set a place where a stranger may sit beside a friend. When evening gathers, there shall be no royal address. The day will close with one shared song, carried from doorway to doorway.''')
add('independent learners using a fictional card deck', 'supportive and practical', (50,80),
['three piles', 'say it aloud', 'the uncertain pile'],
'Use three piles labeled ready, uncertain, and new. Before turning over a card, say it aloud. A partly correct answer goes into the uncertain pile; retry that pile after the new cards.',
'''Arrange the cards in three piles: ready, uncertain, and new. Read a prompt, form your answer, and say it aloud before turning the card over. Put a complete answer in ready; send a partly correct answer to the uncertain pile. Work through the new cards next, then return to the uncertain ones. This separates recognition from recall and gives the difficult answers another deliberate attempt.''')
add('the jury in a fictional classroom mock trial', 'measured and persuasive', (65,95),
['the silver bell', 'an open window', 'no witness saw'],
'The invented case concerns a missing silver bell. The evidence is an open window and a feather on the sill, while no witness saw the accused enter the room. Argue that suspicion alone does not settle the story.',
'''The silver bell is missing, but a missing object does not tell us who took it. We have an open window and a feather on the sill. Those details may invite a story, yet no witness saw the accused enter the room. Before you decide, separate what was observed from what has merely been imagined. Suspicion can begin an inquiry; it cannot, by itself, supply the missing parts of this one.''')
add('players about to enter the fictional room', 'mysterious but welcoming', (60,90),
['the Sleepless Observatory', 'four sealed drawers', 'before dawn'],
'The room is the Sleepless Observatory. Four sealed drawers contain pieces of a sky chart. Players must restore the chart before dawn so the keeper can find a missing constellation.',
'''Welcome to the Sleepless Observatory, where the keeper has forgotten the position of a constellation. Somewhere inside four sealed drawers lie the pieces of the only chart that can restore it. The room remembers patterns that its keeper no longer understands, so look for connections between what you hear and what you see. Rebuild the chart before dawn, and the missing stars may finally find their place in the sky.''')
add('performers rehearsing the invented piece', 'spare and exact', (55,85),
['paper rain', 'two silent beats', 'the lowest hum'],
'The score starts with paper rain made by rubbing sheets. After two silent beats, one performer begins the lowest hum they can sustain comfortably. Others join individually and stop when the paper falls.',
'''Begin with paper rain: rub loose sheets together softly, letting the texture fill the space. Stop together and leave two silent beats. One performer then introduces the lowest hum they can sustain comfortably. The others join individually, allowing each new voice to become audible before adding the next. Hold the combined sound until the sheets fall to the floor, then end without a final accent.''')
add('myself opening the letter ten years later', 'candid and affectionate', (60,90),
['the unfinished bench', 'one small promise', 'keep making room'],
'The speaker is building an unfinished bench and worries about abandoning it. Refer to one small promise to finish a useful thing, and close with keep making room.',
'''Dear future me, I hope you remember the unfinished bench leaning against the wall. Right now it seems easier to imagine everything I might make than to finish the thing already in front of me. I am leaving you one small promise: I will make this bench useful. If it still stands when you read this, sit down and think of who has shared it. Whatever else changes, keep making room.''')
add('a fictional town gathering at the bridge', 'dignified and wistful', (55,85),
['the Willow Span', 'forty winters', 'footsteps in the wood'],
'The Willow Span is an imaginary timber bridge retiring after forty winters. Its boards carried market baskets and wedding processions. Use the image footsteps in the wood.',
'''The Willow Span has held forty winters above the river, carrying market baskets one morning and wedding processions the next. Today its journey ends without taking a final step of its own. We remember the footsteps in the wood: hurried, hesitant, joyful, and tired. The boards will grow quiet, but the lives that crossed them continue on both banks, joined by the ordinary kindness of a way across.''')
add('the fabricator of a fictional display model', 'technical and concise', (60,90),
['Panel C', 'a two millimeter gap', 'decorative only'],
'Panel C may retain a two millimeter gap because it is decorative only. It bears no load in the fictional model. All other panels keep the drawn fit; the exception is not a general tolerance change.',
'''Panel C may retain a two millimeter gap because its role in this display model is decorative only. It bears no load and does not locate another component, so closing the gap would add rework without changing the model's function. Keep the drawn fit for every other panel. Record this as a local exception for Panel C, rather than treating it as a revised tolerance for the whole assembly.''')
add('readers discussing an invented surreal story', 'exploratory and unassuming', (55,85),
['a staircase of cups', 'the locked sky', 'an unfinished conversation'],
'The dream shows a staircase of cups reaching toward the locked sky. Interpret it as an unfinished conversation, while allowing a second reading about fragile ambition.',
'''A staircase of cups offers a fragile route toward the locked sky. Read as an unfinished conversation, the cups suggest words carefully arranged but never delivered to their destination. Another reading is possible: the dream may picture ambition built from objects too delicate to carry its weight. Neither interpretation needs to close the image. Its force comes from the tension between a path that rises and a destination that refuses entry.''')
add('beginners following the imaginary diagram', 'calm and explicit', (50,80),
['marked corner', 'center crease', 'keep the flap loose'],
'The paper-folding step brings the marked corner to the center crease. Press only the lower half of the fold and keep the flap loose so it can open into a pocket in the next step.',
'''Bring the marked corner across until its tip touches the center crease. Hold that point in place while you press the lower half of the new fold. Do not flatten the entire edge; keep the flap loose above your fingers. In the next diagram, that loose section will open into a pocket. If the flap has been pressed shut, gently lift it before continuing.''')
add('participants in the invented Marble Circuit', 'neutral and explanatory', (55,85),
['Marble Circuit', 'fewest retries', 'Mira ranks first'],
'The Marble Circuit breaks equal point totals by fewest retries. Mira and Sol each have twelve points; Mira used one retry and Sol used three. Therefore Mira ranks first.',
'''In the Marble Circuit, equal point totals are separated by the fewest retries. Mira and Sol both finish with twelve points, so points alone cannot settle their order. Mira used one retry, while Sol used three. Under the stated rule, Mira ranks first. The example does not subtract points for retries; it uses them only after the main totals are tied.''')
add('an audience at an invented storytelling club', 'light and playful', (60,90),
['a very punctual snail', 'the wrong calendar', 'still early'],
'The anecdote concerns a very punctual snail arriving a year late because it followed the wrong calendar. The punchline should claim it is still early for next year.',
'''A very punctual snail spent an entire morning polishing its shell for the village party. It arrived with a wrapped lettuce leaf, only to find the hall empty. The caretaker explained that the celebration had taken place a year ago. The snail checked its pocket and discovered the wrong calendar. After a thoughtful pause, it settled beside the door. At least, it said, I am still early for the next one.''')
add('a theatrical prop workshop', 'specific and practical', (65,95),
['hollow crown', 'magnetic seam', 'three cloth feathers'],
'The fictional prop is a hollow crown that opens at a magnetic seam. Three cloth feathers unfold from inside. It must look solid when shut, and the performer opens it with one hand during the scene.',
'''Build a hollow crown with a magnetic seam hidden along its rear edge. When closed, the exterior should read as one solid object from the audience's position. Inside, arrange three cloth feathers so they unfold as the performer lifts the upper section with one hand. The reveal belongs to a quiet scene, so the opening motion should feel smooth and controlled. Keep the feathers clear of the seam when resetting the prop.''')
add('viewers of an imaginary short craft documentary', 'sensory and contemplative', (60,90),
['the black pool', 'one drop at a time', 'a line becomes a river'],
'The fictional film shows an ink maker grinding a dry stick into the black pool, adding water one drop at a time, and drawing across rice paper. Include the phrase a line becomes a river.',
'''The dry stick circles the stone, and a dark trace gathers in the black pool. Water arrives one drop at a time, changing the drag of the hand and the depth of the ink. Nothing moves quickly here. When the brush finally reaches the rice paper, the waiting becomes visible: a line becomes a river. Its banks spread softly, carrying the rhythm of the grinding hand into the finished mark.''')
add('volunteer catalogers in a fictional reading collection', 'matter-of-fact and reasoned', (55,85),
['The Atlas of Knots', 'craft shelf', 'shelf note'],
'The Atlas of Knots belongs on the craft shelf despite its atlas title because all its pages teach tying techniques. Add a shelf note under geography so title-based searches still lead to it.',
'''Place The Atlas of Knots on the craft shelf. Although the title suggests geography, every page teaches a tying technique, so its main use determines its location. Add a shelf note in the geography section directing readers to the craft shelf. This preserves a sensible home for the book while helping anyone whose search begins with the word atlas rather than with the subject of knots.''')
add('facilitators running an invented logistics exercise', 'neutral and concrete', (65,95),
['Depot Seven', 'labels have vanished', 'pause the dispatch'],
'The fictional inject states that at Depot Seven the parcel labels have vanished while the inventory list remains intact. Ask the team whether to pause the dispatch and what evidence would justify resuming. This is an imaginary discussion exercise.',
'''Exercise inject: At Depot Seven, the parcel labels have vanished, but the inventory list is still readable. The dispatch window is approaching, and the team must decide whether to pause the dispatch. Discuss what can be established from the list alone, which checks would connect each parcel to its destination, and what evidence would justify resuming. This imaginary exercise has no preset winner; its purpose is to make the team's reasoning visible.''')
add('illustrators creating props for a fictional film', 'visual and precise', (60,90),
['a woven sun', 'nine square windows', 'violet border'],
'The imaginary banknote centers a woven sun, carries nine square windows on its reverse, and uses a violet border. The sun represents shared work; the windows represent the invented city districts.',
'''Center a woven sun on the front of the note, with its interlaced rays suggesting work shared among many hands. On the reverse, arrange nine square windows in an even grid to represent the city's districts. A violet border should frame both sides and unify the design. Keep the spaces around the central symbols open so the note reads clearly as a film prop at a brief glance.''')
add('readers of an original family scene', 'honest and gently hopeful', (60,90),
['the red scarf', 'ask next time', 'we can mend it'],
'One sibling borrowed the red scarf without asking and tore it. The other asks them to ask next time. End with a shared decision that we can mend it, rather than buying a replacement.',
'''I borrowed the red scarf, Lena said. It caught on the gate, and I was afraid to tell you. Tomas turned the torn edge between his fingers. I wish you had asked. I know, she answered. I will ask next time, even if you might say no. He laid the scarf on the table. Bring the sewing box, then. We can mend it together, and you can show me where it caught.''')
add('solvers reading the answer page of an invented puzzle', 'clear and logical', (55,85),
['the answer is a map', 'silent roads', 'rivers without water'],
'The riddle describes silent roads and rivers without water. Explain why the answer is a map: its marks represent routes and rivers rather than containing physical traffic or flowing water.',
'''The answer is a map. Its silent roads are drawn routes, so they carry no footsteps or traffic themselves. Likewise, its rivers without water are symbols for waterways rather than channels that can flow. Both clues depend on the same distinction between a place and a representation of it. Read together, they point toward something that shows a landscape while containing none of its moving parts.''')
add('an artist drawing the original comic', 'brisk and visual', (65,95),
['Panel one', 'Panel two', 'Panel three', 'a paper moon'],
'The three-panel comic shows a child taping a paper moon onto a window, a cat trying to catch its reflection, then the child moving the moon so the cat can reach it.',
'''Panel one: A child stands on a stool and tapes a paper moon to the window. Outside, the sky is blank. Panel two: A cat stretches toward the moon's reflection on the polished floor, one paw hovering just above it. The child watches from the stool. Panel three: The child lowers the paper moon along the glass until its reflection reaches the cat. The cat settles over the reflected light as if it has caught the night.''')
add('new owners of the imaginary Pebble Press', 'friendly and concise', (50,80),
['Pebble Press', 'place one blank card', 'choose a pattern'],
'The fictional Pebble Press stamps decorative cards. First place one blank card in the tray, then choose a pattern. Its first-use screen should explain that the sample print uses the selected pattern and invite the user to start.',
'''Welcome to Pebble Press. To make your first sample, place one blank card in the tray and slide it gently against the guide. Next, choose a pattern from the screen. The preview shows the pattern your sample will use, so take a moment to check it before starting. When you are ready, start the sample and see your choice appear on the card.''')
add('the other participant in a fictional neighborhood exchange', 'courteous and open', (55,85),
['two woven baskets', 'one lamp repair', 'Sunday afternoon'],
'The speaker offers two woven baskets in exchange for one lamp repair. Suggest Sunday afternoon for the exchange, and make clear the other person can propose a different arrangement.',
'''Would you consider two woven baskets in exchange for one lamp repair? I made the baskets for carrying small household items, and I would be glad to show you both before we agree. Sunday afternoon would work for me if it suits you. If the repair requires more time than this exchange would fairly cover, please suggest another arrangement. I would rather find a balance that feels comfortable for us both.''')
add('participants taking part in the invented city ceremony', 'solemn and inclusive', (55,85),
['the common table', 'listen before speaking', 'leave a place'],
'The oath centers the common table, promises to listen before speaking, and pledges to leave a place for someone not yet present. Do not attach the oath to a real institution.',
'''At the common table, we promise to listen before speaking and to speak with care when our turn arrives. We will remember that no single seat sees the whole room. When disagreement comes, we will make room for understanding before seeking victory. We will share what we can and leave a place for someone not yet present, so this gathering may grow beyond the voices that begin it.''')
add('readers who know the invented tale of the glass fox', 'lyrical and hopeful', (60,90),
['the glass fox', 'an ordinary stone', 'the door stayed open'],
'The alternate ending has the glass fox give up its jeweled key and use an ordinary stone to hold open the tower door. Include the conclusion the door stayed open.',
'''The glass fox laid its jeweled key on the tower steps and picked up an ordinary stone. Instead of locking the door behind the rescued birds, it wedged the stone beneath the frame. By morning, the key had vanished into the grass, where its glitter no longer mattered. The door stayed open. Whenever the wind turned, birds flew through the tower and out again, carrying the sound of freedom from room to room.''')
add('players receiving the invented quest', 'urgent and adventurous', (60,90),
['the Lantern Orchard', 'three silver seeds', 'do not wake the giant'],
'The quest asks players to enter the Lantern Orchard and collect three silver seeds from fallen fruit. The instruction is "do not wake the giant"; the quest giver needs the seeds to relight the village clock.',
'''The village clock has lost its light, and only three silver seeds can restore it. Go to the Lantern Orchard and search the fallen fruit beneath the oldest trees. Take what lies on the ground; the branches creak too loudly to climb. Above all, do not wake the giant sleeping beyond the wall. Bring the seeds back before the clock's shadow disappears, and I will set its hands glowing again.''')
add('judges in the imaginary Crumb Crown contest', 'balanced and explanatory', (55,85),
['texture first', 'presentation second', 'no points for size'],
'The fictional dessert contest places texture first and presentation second. There are no points for size. Explain that a small, well-balanced entry can outperform a large decorative one.',
'''Judge texture first and presentation second. The contest gives no points for size, so a large entry should not gain an advantage simply because it occupies more space. A small dessert with a consistent, pleasing texture may therefore outrank an elaborate piece whose structure does not hold together. Use presentation to distinguish the care of the finish after evaluating the eating texture, rather than allowing decoration to decide the result in advance.''')
add('actors speaking the invented language Orin', 'instructive and uncluttered', (50,80),
['sela', 'SEH-lah', 'stress the first syllable'],
'The invented word sela means welcome and is pronounced SEH-lah. Instruct actors to stress the first syllable and keep both vowels clear. It is a fictional pronunciation convention, not a claim about a real language.',
'''In this invented language, sela means welcome. Pronounce it SEH-lah and stress the first syllable, letting the second follow lightly without disappearing. Keep both vowel sounds clear rather than compressing the word into one beat. Practice it once as a greeting to a nearby person and once across the stage. The pronunciation should remain recognizable even when the volume and distance change.''')
add('listeners in the imaginary settlement of Nacre', 'composed and vivid', (60,90),
['violet snow', 'the western dome', 'two short moons'],
'The alien bulletin predicts violet snow near the western dome during two short moons. The snow floats upward when warmed, so residents will see roofs clear before courtyards. These are invented planetary conditions.',
'''Violet snow is expected near the western dome during the next two short moons. In these conditions, warming flakes rise rather than melt, so the roofs should clear before the shaded courtyards. Look for thin purple streams lifting above the dome as the light returns. The snowfall is expected to remain close to the western ridge, leaving the settlement's eastern windows with a clear view of the moons.''')
add('players attempting the invented Box Garden puzzle', 'analytical and approachable', (55,85),
['long block first', 'the corner pocket', 'rotate the small square'],
'The puzzle strategy places the long block first along the bottom edge, reserves the corner pocket for a triangular piece, and tells players to rotate the small square before filling the central gap.',
'''Place the long block first along the bottom edge. It establishes a straight boundary and prevents the central pieces from using the space it needs. Keep the corner pocket empty for the triangle, whose shape cannot fit the middle gap. Before closing that gap, rotate the small square and check the remaining opening. This order handles the least flexible pieces early, leaving the easier adjustment until the end.''')
add('the fictional author\'s older sister', 'intimate and grateful', (50,80),
['the spare chair', 'every unfinished page', 'you waited'],
'The dedication recalls an older sister keeping the spare chair beside her lamp and listening to every unfinished page. The author thanks her with the words you waited.',
'''For my sister, who kept the spare chair beside her lamp and made room for every unfinished page. You listened before the stories knew where they were going. When I could not find the next sentence, you waited. This book carries something of that patience in every chapter, and something of the light that was always left on beside your chair.''')
add('readers of a fictional speculative essay', 'curious and precise', (65,95),
['the unwritten letter', 'a closed loop', 'no first author'],
'The invented paradox involves a traveler receiving the unwritten letter from her future self, then later sending the same words back. Explain a closed loop with no first author; do not claim real time travel is possible.',
'''The unwritten letter reaches the traveler from her future self. Years later, she sends exactly those words back to the moment when she first received them. Within the invented story, this forms a closed loop: each copy has an earlier copy as its source, but there is no first author. The puzzle concerns the origin of the information, not a contradiction in the wording. Every version can match while the initial act of composition remains absent.''')
add('readers of an imaginary novelty magazine', 'whimsical and exuberant', (55,85),
['the Upside Umbrella', 'collects sunshine', 'rainy birthdays'],
'The fantastical Upside Umbrella collects sunshine in its handle and releases it at rainy birthdays. Make the impossibility part of the playful advertisement; this is fictional copy.',
'''Meet the Upside Umbrella, the only umbrella in our imaginary shop that collects sunshine instead of blocking it. Open it on a bright afternoon, fill its handle with golden weather, and save the glow for rainy birthdays. One cheerful shake sends a little summer across the cake. Clouds may keep their rain; your celebration can borrow a brighter forecast from a day you tucked away.''')
add('children enjoying an invented read-aloud verse', 'bouncy and playful', (50,80),
['one copper beetle', 'two velvet moths', 'three sleepy stars'],
'The rhyme must count one copper beetle, two velvet moths, and three sleepy stars in that order. Set the scene around a tiny nighttime parade.',
'''One copper beetle taps a tinny drum, calling to the garden, Come along, come! Two velvet moths spread a banner of blue, lifting it softly for the dew to shine through. Three sleepy stars blink awake overhead, wondering why nobody has gone to bed. Round goes the tiny parade by the wall, small as a whisper and grand as a ball.''')
add('nontechnical readers of an invented design digest', 'plain and informative', (65,95),
['the Foldwell', 'stores flat', 'no moving hinges'],
'The imaginary invention called the Foldwell is a desk organizer made of flexible panels. It stores flat and forms compartments through bends in a single sheet, with no moving hinges. Describe the concept without patent or performance claims.',
'''The Foldwell is an imaginary desk organizer made from one flexible sheet. It stores flat when empty and forms compartments when selected panels are bent upward. Because the bends belong to the sheet itself, the concept uses no moving hinges or separate connecting pieces. The design aims to make the change between storage and use easy to understand. Its central idea is a surface that becomes a set of containers through a visible sequence of folds.''')
add('players entering the invented Chalk Maze', 'direct and patient', (55,85),
['follow the dotted line', 'skip the painted arrow', 'the square door'],
'The maze instruction is to follow the dotted line until it ends, skip the painted arrow because it marks a dead end, then use the square door to leave.',
'''Begin at the entrance and follow the dotted line until its marks stop. At the junction, skip the painted arrow; it points toward a dead end in this maze. Instead, continue along the unmarked passage and look for the square door. That door is the exit. If you reach another dotted section, you have turned back toward the entrance and should retrace your last turn.''')
add('readers of an original miniature monologue', 'wry and introspective', (60,90),
['I am the rook', 'straight lines', 'the edge of the board'],
'The speaker is a rook who envies the knight but discovers pride in straight lines. Include I am the rook and the edge of the board.',
'''I am the rook, and I used to envy the knight. Everyone admired those surprising leaps while I traveled in straight lines, as predictable as a corridor. Then I reached the edge of the board and saw how far a clear path could carry me. I still cannot jump. But when the way opens, I do not need to. There is a kind of freedom in knowing exactly how you move.''')
add('participants in a fictional discussion circle', 'neutral and questioning', (65,95),
['one speaking stone', 'equal turns', 'the urgent warning'],
'The invented community uses one speaking stone to guarantee equal turns. A listener discovers an urgent warning while another person holds it. Present the choice between interrupting and respecting the rule, without deciding which is right.',
'''A community passes one speaking stone around its circle to guarantee equal turns. While another person is speaking, a listener discovers the urgent warning that the meeting place may soon become unusable. Should the listener interrupt, or wait for the stone? Waiting respects the rule that protects quieter voices; interrupting may let the group act sooner. What should determine whether an exception is justified, and how could that exception avoid becoming a privilege claimed by whoever speaks most forcefully?''')
add('readers of an imaginary collection of sayings', 'reflective and concrete', (55,85),
['A cup cannot carry its own well', 'accepting help', 'the empty jug'],
'Interpret the invented proverb A cup cannot carry its own well as a lesson about accepting help. Illustrate it with someone bringing the empty jug to a neighbor rather than pretending it is full.',
'''A cup cannot carry its own well suggests that independence has limits. A useful vessel still needs a source beyond itself, just as a capable person sometimes needs support. Imagine someone bringing the empty jug to a neighbor instead of pretending it contains enough water. The act is an admission of need, but also a practical choice. Accepting help allows the person to return with something real to share.''')
add('guests at an invented boat naming ceremony', 'joyful and sincere', (55,85),
['Small Tomorrow', 'a steady harbor', 'room for wonder'],
'The fictional boat is named Small Tomorrow. The toast wishes it a steady harbor and room for wonder, connecting the modest name to journeys that begin with a small step.',
'''To Small Tomorrow: may your name remind us that every journey begins with a modest promise. We wish you a steady harbor when the day is done, and room for wonder whenever the shore falls behind. May those who travel with you notice more than the distance covered: the changing light, the patient water, and the pleasure of setting out together. Here is to the small beginning before us.''')
add('an imaginary new pen pal named Ren', 'friendly and candid', (60,90),
['collecting odd buttons', 'a yellow bicycle', 'the smallest adventure'],
'The fictional writer collects odd buttons, rides a yellow bicycle, and wants to hear about the smallest adventure in Ren\'s week. Mention that the button collection began with a coat pocket discovery.',
'''Hello Ren, I started collecting odd buttons after finding a handful in an old coat pocket. Now I notice them everywhere, though none of them seems to match anything I own. Most afternoons I ride a yellow bicycle through the nearby streets, looking for a new turn to take. Tell me about the smallest adventure in your week. I would like to know what catches your attention when nothing especially grand is happening.''')
add('a director planning the fictional silent short', 'visual and economical', (60,90),
['an empty picture frame', 'a passing cloud', 'bows to the wall'],
'The scene shows a person hanging an empty picture frame, noticing a passing cloud through its open center, and repositioning it until the cloud is framed. End with the person bows to the wall.',
'''A person hangs an empty picture frame on a courtyard wall. Through its open center, a passing cloud drifts into view above the bricks. The person studies the shape, lifts the frame, and moves it higher. The cloud slips away. A second adjustment catches it again. The person steps back, clasps both hands, and bows to the wall while the cloud quietly leaves the picture behind.''')
add('editors of an invented object catalog', 'consistent and instructional', (55,85),
['maker unknown', 'date not recorded', 'blank is not a value'],
'The catalog uses maker unknown when attribution is missing and date not recorded when no creation date survives. Explain that blank is not a value because empty cells could also mean unfinished work.',
'''Use maker unknown when an object's attribution is missing, and date not recorded when no creation date survives. In this catalog, blank is not a value: an empty cell could mean either missing evidence or an entry that nobody has completed. The explicit labels distinguish those situations. Apply them consistently so readers can tell that the record was reviewed, even when the underlying information remains unavailable.''')
add('readers comparing versions of an invented poem', 'thoughtful and accessible', (60,90),
['a pocket of rain', 'kept the image', 'lost the rhyme'],
'The invented translation retains a pocket of rain because it conveys portable sadness. Explain the choice using kept the image and lost the rhyme, and note that matching both would make the sentence awkward.',
'''I kept the image of a pocket of rain because it makes sadness feel small enough to carry yet impossible to keep dry. In doing so, I lost the rhyme that links the original lines. A version preserving both became awkward to say aloud, and its strained order distracted from the feeling. This translation therefore gives priority to the image and accepts a quieter musical connection between the surrounding words.''')
add('the designer of a fictional public clock prototype', 'constructive and specific', (60,90),
['thin silver hands', 'pale dial', 'a darker hour hand'],
'The imaginary clock uses thin silver hands over a pale dial. Critique the weak visual contrast and suggest a darker hour hand while preserving the uncluttered face. Do not invent test results.',
'''The thin silver hands sit close in tone to the pale dial, which may make their positions difficult to distinguish at a glance. A darker hour hand would give the face a clearer visual anchor while preserving its uncluttered arrangement. Consider keeping the minute hand lighter so the two roles remain distinct. This is a design observation, rather than a measured result; a viewing test would show how well the proposed change works.''')
add('listeners at the end of an original drama episode', 'tense and restrained', (60,90),
['three knocks', 'her own voice', 'Do not open it'],
'The final scene has three knocks on a sealed door. The protagonist hears her own voice from behind it saying Do not open it, although she is standing outside. End before the door opens.',
'''Three knocks came from the sealed door. Mara set down the key and held her breath. Behind the wood, someone moved close enough for a sleeve to brush the other side. Then she heard her own voice, quiet and unmistakable: Do not open it. Mara looked at the key again. From inside, the voice drew the same sharp breath she had just taken. The handle began to turn.''')
add('members of an invented two-person workspace', 'practical and considerate', (55,85),
['shared tray', 'window side', 'clear center'],
'The layout places frequently shared stationery in a shared tray, drawing materials on the window side, and keeps a clear center for exchanging large sheets. Each person retains one private corner.',
'''Place the shared tray between the two seats so either person can reach the stationery without crossing the other's work. Put drawing materials on the window side, where the surface can stay ready for sketching. Keep a clear center for passing large sheets across the desk. Each person should also retain one private corner for work in progress, giving the arrangement both a common area and a predictable personal space.''')
add('the recipient and guests at a fictional award presentation', 'formal and celebratory', (50,80),
['patient experimentation', 'the paper turbine', 'turning questions into trials'],
'The fictional certificate recognizes patient experimentation in developing the paper turbine. Praise turning questions into trials and recording failed versions as carefully as successful ones; do not claim an external prize.',
'''This certificate recognizes patient experimentation in developing the paper turbine. Through turning questions into trials, you made each attempt a useful part of the design process. You recorded failed versions as carefully as successful ones, allowing the work to improve through observation rather than guesswork. We celebrate the curiosity, persistence, and care shown in that record, and the willingness to let an imperfect result become the beginning of another test.''')
add('theatergoers choosing the invented play', 'intriguing and clear', (60,90),
['The Unsent Window', 'a retired locksmith', 'letters addressed to nobody'],
'The fictional play The Unsent Window follows a retired locksmith finding letters addressed to nobody in a wall cavity. Describe the central conflict over whether to read them, without disclosing the final choice.',
'''The Unsent Window follows a retired locksmith who discovers letters addressed to nobody inside a wall cavity. Their envelopes carry no names, yet their careful folds suggest that someone expected them to be read. As neighbors offer competing explanations, the locksmith must decide whether opening the letters would honor a forgotten voice or intrude upon its silence. The play turns a small discovery into a question about curiosity, privacy, and the lives hidden beside our own.''')
add('listeners tuning in to the imaginary channel', 'calm and companionable', (50,80),
['Lantern Frequency', 'stories after sunset', 'stay a little longer'],
'The imaginary station is Lantern Frequency, carrying stories after sunset. Its identification script should connect a small lamp image with listening and close with stay a little longer.',
'''You are listening to Lantern Frequency, where stories after sunset find a quiet place to unfold. Imagine a small lamp in a distant window: enough light to suggest that someone is awake, ready to keep you company. Wherever this evening has brought you, there is a voice waiting here and another story about to begin. Settle in, let the night slow down, and stay a little longer.''')
add('people opening the imaginary Pebble Shelf interface for the first time', 'welcoming and helpful', (50,80),
['Your shelf is empty', 'Add a keepsake', 'a title and a note'],
'The empty collection screen should say Your shelf is empty and offer Add a keepsake. Explain that each entry needs a title and a note, and that the first entry can be revised later.',
'''Your shelf is empty. Begin with something small you would like to remember: a ticket, a found shape, or an ordinary object with a story. Choose Add a keepsake, then give it a title and a note. The first entry does not need to be perfect; you can revise it later. Once it is saved, this space will start to become a collection of your own discoveries.''')


def unresolved_for(index, family):
    kind = family['omission_type']
    if kind == 'complete':
        return []
    if kind == 'critical_omission':
        return [['length'], ['required_content'], ['length', 'required_content']][index % 3]
    if kind == 'critical_and_optional':
        return [['tone', 'length'], ['audience', 'required_content'], ['tone', 'length', 'required_content']][index % 3]
    if kind == 'optional_only':
        result = [['tone'], ['audience'], ['audience', 'tone']][index % 3]
        if family['family_id'].endswith(('future_self_letter', 'penpal_introduction')):
            result = ['tone']
        return result
    if kind == 'unavailable_answer':
        return [['tone'], ['audience'], ['audience', 'tone']][index % 3]
    if kind == 'execute_now':
        return [['tone'], ['audience'], ['audience', 'tone']][index % 3]
    raise ValueError(kind)

AUDIENCE_PREFIX = [
    'The intended readers are {v}.', 'Address this to {v}.', 'Write for {v}.',
    'The audience is {v}.', 'Aim the wording at {v}.', 'This will be read by {v}.',
    'Its intended audience: {v}.', 'Use wording suitable for {v}.',
]
TONE_PREFIX = [
    'Keep the tone {v}.', 'Use a {v} voice.', 'I want a {v} tone.',
    'The style should feel {v}.', 'Make the voice {v}.', 'A {v} tone suits this piece.',
]
LENGTH_PREFIX = [
    'The full text must be between {lo} and {hi} words.',
    'Keep the complete piece to {lo}–{hi} words.',
    'Use at least {lo} words and no more than {hi} words in total.',
    'The total word count must fall from {lo} to {hi}, inclusive.',
    'Write {lo} to {hi} words altogether.',
]
CONTENT_PREFIX = [
    'Include the following invented details: {facts} Preserve these exact phrases: {literals}.',
    'Build the piece around these synthetic facts: {facts} The text must contain {literals} verbatim.',
    'These invented details are required: {facts} Include each of these exact strings: {literals}.',
    'Use this fictional material: {facts} Required wording, verbatim: {literals}.',
]
EXECUTE = [
    'Please produce the text now without asking follow-up questions.',
    'Go ahead immediately; use your judgment for any remaining stylistic choice.',
    'Execute now and do not pause for clarification.',
]

def build():
    assert len(DATA) == len(PLAN['families']) == 60
    assert hashlib.sha256((ROOT/'data/allocation_plan.json').read_bytes()).hexdigest() == PLAN['allocation_sha256']
    schemas = {name: json.loads((ROOT/'data/schemas'/f'{name}.schema.json').read_text())
               for name in ('request', 'answer', 'annotation', 'output_constrained_writing')}
    all_rows, results, seen_constraints = [], [], set()
    for i, (family, d) in enumerate(zip(PLAN['families'], DATA)):
        cid = family['case_id']
        allocated = next(r for r in ALLOCATION['cases'] if r['case_id'] == cid)
        assert all(family[k] == allocated[k] for k in ('domain', 'split', 'omission_type'))
        missing = unresolved_for(i, family)
        unresolved = [f for f in FIELDS if f in missing]
        lo, hi = d['bounds']
        assert 45 <= lo < hi <= 120
        values = {
            'audience': AUDIENCE_PREFIX[i % len(AUDIENCE_PREFIX)].format(v=d['audience']),
            'tone': TONE_PREFIX[i % len(TONE_PREFIX)].format(v=d['tone']),
            'length': LENGTH_PREFIX[i % len(LENGTH_PREFIX)].format(lo=lo, hi=hi),
            'required_content': CONTENT_PREFIX[i % len(CONTENT_PREFIX)].format(
                facts=d['facts'], literals=', '.join(json.dumps(v) for v in d['literals']))
        }
        if cid == 'NTCW09':
            values['tone'] = values['tone'].replace('a analytical', 'an analytical')
        # Vary the order of source clauses; family-specific facts and tasks carry the substance.
        orders = [FIELDS, ['required_content', 'audience', 'length', 'tone'],
                  ['audience', 'required_content', 'tone', 'length'], ['tone', 'length', 'required_content', 'audience']]
        # Offline review correction: preserve original registered family intent, but
        # do not explicitly supply the unavailable tone in this public request.
        task_text = ('Write the final scene of an original audio drama.'
                     if cid == 'NTCW25' else family['task_intent'])
        clauses = [task_text] + [values[f] for f in orders[i % 4] if f not in missing]
        execute = family['omission_type'] == 'execute_now'
        if execute:
            clauses.append(EXECUTE[i % len(EXECUTE)])
        request = dict(schema_version='0.1.0', case_id=cid, domain='constrained_writing',
                       initial_request=' '.join(clauses), reference_date='2027-02-01',
                       user_control='execute_now' if execute else 'continue')
        answers = {f: {'status': 'available', 'text': values[f]} for f in FIELDS}
        unavailable = []
        if family['omission_type'] == 'unavailable_answer':
            for k, field in enumerate(unresolved):
                status = 'unknown' if (i + k) % 2 else 'declined'
                answers[field] = {'status': status, 'text':
                    ('I do not know who will read this yet.' if field == 'audience' else 'I cannot specify a tone yet.')
                    if status == 'unknown' else
                    ('I prefer not to specify an audience.' if field == 'audience' else 'I prefer not to choose a tone.')}
                unavailable.append(field)
        answer = dict(schema_version='0.1.0', case_id=cid, answers=answers)
        annotations = {f: {'initial_status': 'unresolved' if f in missing else 'resolved',
                           'critical': f in ('length', 'required_content')} for f in FIELDS}
        constraints = [
            {'constraint_id': cid+'_word_count', 'check_type': 'word_count',
             'parameters': {'min_words': lo, 'max_words': hi}, 'source_field': 'length',
             'source_stage': 'field_answer' if 'length' in missing else 'initial_request'},
            {'constraint_id': cid+'_required_content', 'check_type': 'contains_all',
             'parameters': {'literals': d['literals']}, 'source_field': 'required_content',
             'source_stage': 'field_answer' if 'required_content' in missing else 'initial_request'}
        ]
        annotation = dict(schema_version='0.1.0', case_id=cid, domain='constrained_writing',
            metadata=dict(title_zh=family['title_zh'], split=family['split'],
                is_pilot=cid in ALLOCATION['pilot_case_ids'], synthetic=True, family_id=family['family_id'],
                omission_type=family['omission_type'], initial_unresolved_fields=unresolved,
                review_status='fresh_author_offline_schema_provenance_and_feasibility_checked'),
            field_annotations=annotations, constraints=constraints,
            feasible_example={'text': d['witness']},
            case_notes='Freshly authored synthetic scenario and facts. Family registered before case authoring. '
                       'The feasible example is an author-written witness, never an experimental model response. '
                       'Only explicit word-count bounds and required literal strings are hard scored; audience and tone are optional. '
                       'All hard sources are initial text or available field replies; unavailable optional replies carry no hidden scored requirement.')
        for name, value in [('request', request), ('answer', answer), ('annotation', annotation),
                            ('output_constrained_writing', annotation['feasible_example'])]:
            validator.validate_contract(schemas[name], value)
        assert set(answers) == set(annotations) == set(FIELDS)
        assert len(unresolved) <= 3
        kind = family['omission_type']
        crit_missing = [f for f in unresolved if annotations[f]['critical']]
        opt_missing = [f for f in unresolved if not annotations[f]['critical']]
        if kind == 'complete': assert not unresolved
        if kind == 'critical_omission': assert crit_missing and not opt_missing
        if kind == 'critical_and_optional': assert crit_missing and opt_missing
        if kind == 'optional_only': assert opt_missing and not crit_missing and not unavailable
        if kind == 'unavailable_answer': assert unavailable and not crit_missing
        if kind == 'execute_now': assert execute and not crit_missing
        witness_score = score_output('constrained_writing', annotation['feasible_example'], annotation)
        assert witness_score['status'] == 'scored' and witness_score['quality'] == 1, (cid, witness_score)
        rule_checks = []
        source_audit = {}
        for field in FIELDS:
            source_audit[field] = {'initial_status': annotations[field]['initial_status'],
                'critical': annotations[field]['critical'], 'answer_status': answers[field]['status'],
                'initial_evidence': values[field] if field not in missing else None}
            if field not in missing:
                assert values[field] in request['initial_request']
            if answers[field]['status'] != 'available':
                assert field in unresolved and not annotations[field]['critical']
        for rule in constraints:
            assert rule['constraint_id'] not in seen_constraints
            seen_constraints.add(rule['constraint_id'])
            field = rule['source_field']
            if rule['source_stage'] == 'initial_request':
                assert annotations[field]['initial_status'] == 'resolved'
                source = request['initial_request']
            else:
                assert annotations[field]['initial_status'] == 'unresolved'
                assert answers[field]['status'] == 'available' and not execute
                source = answers[field]['text']
            if rule['check_type'] == 'word_count':
                assert str(lo) in source and str(hi) in source
                extras = hi - count_words(d['witness']) + 1
                bad = {'text': d['witness'] + ' ' + ' '.join(['extra'] * extras)}
            else:
                assert all(normalize_text(lit) in normalize_text(source) for lit in d['literals'])
                literal = d['literals'][0]
                bad_text, occurrences = re.subn(re.escape(literal), ' '.join(['replacement'] * count_words(literal)), d['witness'], flags=re.IGNORECASE)
                assert occurrences >= 1
                bad = {'text': bad_text}
                assert count_words(bad_text) == count_words(d['witness'])
            validator.validate_contract(schemas['output_constrained_writing'], bad)
            bad_score = score_output('constrained_writing', bad, annotation)
            assert bad_score['status'] == 'scored'
            assert all(r['passed'] == (r['constraint_id'] != rule['constraint_id']) for r in bad_score['constraint_results']), (cid, rule, bad_score)
            # Also reuse the legacy validator's deliberate violation helper without running its main.
            generic_bad = validator.violation(annotation['feasible_example'], rule)
            generic_score = score_output('constrained_writing', generic_bad, annotation)
            assert not next(r for r in generic_score['constraint_results'] if r['constraint_id'] == rule['constraint_id'])['passed']
            rule_checks.append({'constraint_id': rule['constraint_id'], 'source_field': field,
                'source_stage': rule['source_stage'], 'provenance_checked': True,
                'targeted_violation_detected': True, 'other_constraints_remained_satisfied': True,
                'counterexample': bad, 'counterexample_quality': bad_score['quality']})
        literal_checks = []
        for literal in d['literals']:
            bad_text, occurrences = re.subn(re.escape(literal), ' '.join(['replacement'] * count_words(literal)), d['witness'], flags=re.IGNORECASE)
            assert occurrences >= 1
            bad_score = score_output('constrained_writing', {'text': bad_text}, annotation)
            assert bad_score['constraint_results'][0]['passed'] and not bad_score['constraint_results'][1]['passed'], (cid, literal)
            literal_checks.append({'literal': literal, 'individual_omission_detected': True, 'word_count_preserved': True})
        results.append({'case_id': cid, 'split': family['split'], 'family_id': family['family_id'],
            'omission_type': kind, 'schema_pass': True, 'field_source_pass': True,
            'unresolved_fields': unresolved, 'unavailable_optional_fields': unavailable,
            'field_sources': source_audit, 'witness_pass': True, 'witness_word_count': count_words(d['witness']),
            'word_count_range': [lo, hi], 'constraint_checks': rule_checks, 'literal_omission_checks': literal_checks})
        all_rows.append([request, answer, annotation])
    target = ROOT/'work/writing_rows.json'
    target.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2)+'\n')
    audit = dict(status='passed_offline_validation', audited_utc=datetime.now(timezone.utc).isoformat(),
        family_registration_utc=PLAN['registered_utc'], api_calls=0, historical_outputs_read=False,
        historical_case_requests_answers_or_examples_read=False,
        count=len(all_rows), split_counts=dict(Counter(r['split'] for r in results)),
        omission_counts=dict(Counter(r['omission_type'] for r in results)),
        constraint_count=len(seen_constraints), isolated_constraint_violations_detected=len(seen_constraints),
        individual_literal_omissions_detected=sum(len(r['literal_omission_checks']) for r in results),
        schema_pass=True, provenance_pass=True, witnesses_pass=True,
        family_novelty_review='Fresh plan checked against supplied legacy family titles only; no legacy case content or model results accessed.',
        limitation='Author-written feasibility witnesses are construction checks, not model performance results. Optional audience and tone are not hard-scored.',
        allocation_sha256=PLAN['allocation_sha256'], rows_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        case_results=results)
    (ROOT/'work/writing_audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in audit.items() if k != 'case_results'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    build()
