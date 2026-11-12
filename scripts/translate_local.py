# -*- coding: utf-8 -*-
"""
Tradutor local de roteiros (pt -> en, es) para o historico de projetos.

Gera script_en.json e script_es.json a partir de script.json, com traducoes
feitas pelo proprio modelo (qualidade humana), sem usar Gemini Web/Chrome CDP.

Uso:
  python scripts/translate_local.py              # todos que faltam
  python scripts/translate_local.py --only <slug>
  python scripts/translate_local.py --force
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = Path(r"E:\videomaker\projects")

# ---------------------------------------------------------------------------
# Traducoes feitas pelo modelo (qualidade humana).
# Chave = slug do projeto. Valor = dict com "title", "en" e "es",
# cada um sendo uma lista de dicts com "id" e "text" (apenas secoes que
# diferem do portugues; secoes ausentes sao copiadas do script pt).
# ---------------------------------------------------------------------------

TRADUCOES = {
    "bulldog-ingles-o-cachorro-mais-pregu-60a7": {
        "title_en": "English Bulldog: the laziest and cutest dog in the world",
        "title_es": "Bulldog inglés: el perro más perezoso y adorable del mundo",
        "secao": [
            {"id": "s1", "text_en": "Have you ever seen a thirty-kilo mountain refuse its own food?", "text_es": "¿Has visto alguna vez una montaña de treinta kilos rechazar su propia comida?"},
            {"id": "s2", "text_en": "Despite weighing only ten little kilos against Frida's thirty...", "text_es": "A pesar de pesar solo diez kilitos contra los treinta de ella..."},
            {"id": "s3", "text_en": "But Frida's official superpower is laziness at Olympic level...", "text_es": "Pero el superpoder oficial de Frida es la pereza a nivel olímpico..."},
            {"id": "s4", "text_en": "Will there be anything capable of moving this furry statue?", "text_es": "¿Habrá algo capaz de mover esta estatua peluda?"},
            {"id": "s5", "text_en": "Of course Luna doesn't let this culinary audacity slide!", "text_es": "¡Claro que Luna no deja pasar esta audacia culinaria!"},
            {"id": "s6", "text_en": "The life of these two follows the relentless pace of a Monday...", "text_es": "La vida de estas dos sigue el ritmo implacable de un lunes..."},
            {"id": "s7", "text_en": "Did you know Frida's ancestors were brave athletes?", "text_es": "¿Sabías que los antepasados de Frida eran atletas valientes?"},
            {"id": "s8", "text_en": "But the supreme test happens now in the living room: the big sofa...", "text_es": "Pero la prueba suprema sucede ahora en la sala: el sofá grande..."},
            {"id": "s9", "text_en": "And like every great cartoon friendship, the confusion...", "text_es": "Y como toda gran amistad de dibujos animados, la confusión..."},
            {"id": "s10", "text_en": "In the end, we learn that true friendship doesn't depend on...", "text_es": "Al final, aprendemos que la verdadera amistad no depende de..."},
        ],
    },
    "caes-de-resgate-como-eles-encontram-pess": {
        "title_en": "The SuperSnouts in Action!",
        "title_es": "¡Los SuperFocinhos en Acción!",
        "secao": [
            {"id": "s0", "text_en": "Hi little friends and little friends! How are you? It's great that you're here!", "text_es": "¡Hola, amiguitos y amiguitas! ¿Cómo están? ¡Qué bueno que estén aquí!"},
            {"id": "s1", "text_en": "Have you ever tried to find a hidden toy in the room with...", "text_es": "¿Alguna vez has intentado encontrar un juguete escondido en el cuarto con...?"},
            {"id": "s2", "text_en": "When an earthquake happens, the earth shakes and many stones...", "text_es": "Cuando ocurre un terremoto, la tierra se sacude y muchas piedras..."},
            {"id": "s3", "text_en": "A little rescue dog's nose is a thousand times stronger than...", "text_es": "El nariz de un perrito de rescate es mil veces más fuerte que..."},
            {"id": "s4", "text_en": "Do you know what the secret is? For the little dogs, training is...", "text_es": "¿Sabes cuál es el secreto? Para los perritos, el entrenamiento..."},
            {"id": "s5", "text_en": "They walk very carefully over the loose stones. And...", "text_es": "Caminan con mucho cuidado sobre las piedras sueltas. Y..."},
            {"id": "s6", "text_en": "When the little dog finds the person, he gives the signal! He warns...", "text_es": "Cuando el perrito encuentra a la persona, ¡da la señal! Él avisa..."},
            {"id": "s7", "text_en": "Firefighters and paramedics hear the bark and run to dig...", "text_es": "Los bomberos y socorristas escuchan el ladrido y corren a cavar..."},
            {"id": "s8", "text_en": "After a full day of hard work, these brave little friends...", "text_es": "Después de un día lleno de trabajo duro, estos valientes amiguitos..."},
            {"id": "s_outro", "text_en": "Thank you so much for watching our videos, a big kiss on your heart!", "text_es": "¡Muchas gracias por ver nuestros videos, un gran beso en tu corazón!"},
        ],
    },
    "dachshund-marrom-luna-tenta-pegar-o-bisc": {
        "title_en": "Luna and the Cookie Mission",
        "title_es": "Luna y la Misión Galleta",
        "secao": [
            {"id": "s0", "text_en": "Hello, family! This is Frida and Luna's channel, with another...", "text_es": "¡Hola, familia! Este es el canal de Frida y Luna, con otro..."},
            {"id": "s1", "text_en": "It all started on a quiet afternoon. Luna, our sausage dog...", "text_es": "Todo empezó una tarde tranquila. Luna, nuestra salchicha..."},
            {"id": "s2", "text_en": "But Luna never gives up! She analyzed the terrain. She looked...", "text_es": "Pero Luna nunca se rinde. Analizó el terreno. Miró..."},
            {"id": "s3", "text_en": "The target was clear: the cookie jar! The problem was the height...", "text_es": "El objetivo era claro: el tarro de galletas. El problema era la altura..."},
            {"id": "s4", "text_en": "From up there on the box, Luna prepared! The jar seemed so...", "text_es": "Desde arriba de la caja, Luna se preparó! El tarro parecía tan..."},
            {"id": "s4b", "text_en": "Almost, but not! Hahaha! Luna grabbed the edge of the jar with...", "text_es": "Casi, pero no! ¡Jeje! Luna agarró el borde del tarro con..."},
            {"id": "s5", "text_en": "With a loud noise, Luna and the box fell on the floor! Hahaha! Qu...", "text_es": "Con un gran ruido, Luna y la caja cayeron al suelo! ¡Jeje! Qu..."},
            {"id": "s6", "text_en": "Mission accomplished, the crooked way! Hahaha! Luna, all proud...", "text_es": "Misión cumplida, a la manera torcida! ¡Jeje! Luna, toda orgullosa..."},
        ],
    },
    "o-dia-em-que-a-dachshund-marrom-luna-cav": {
        "title_en": "Luninha's Incredible Tunnel",
        "title_es": "El Increíble Túnel de Luninha",
        "secao": [
            {"id": "s0", "text_en": "Hi little friend! How are you? Great to see you here!", "text_es": "¡Hola, amiguito! ¿Cómo estás? ¡Qué bueno verte aquí!"},
            {"id": "s1", "text_en": "It all started on a sunny day in the yard! The dog Luna...", "text_es": "Todo empezó un día soleado en el patio. La perra Luna..."},
            {"id": "s2", "text_en": "Luna looked at her own little short paws and had an idea...", "text_es": "Luna miró sus propias patitas cortas y tuvo una idea..."},
            {"id": "s3", "text_en": "Suddenly, the English bulldog Frida appeared walking very...", "text_es": "De repente, apareció la bulldog inglesa Frida caminando muy..."},
            {"id": "s4", "text_en": "The hole was getting deeper and longer! Luna en...", "text_es": "El agujero se estaba haciendo más profundo y más largo! Luna en..."},
            {"id": "s5", "text_en": "Frida decided to lend a hand to her adventure companion...", "text_es": "Frida decidió ayudar un poco a su compañera de aventura..."},
            {"id": "s6", "text_en": "Luna gave the last paw and... Plop! The little dog's head...", "text_es": "Luna dio la última pata y... ¡Plop! La cabeza de la perrita..."},
            {"id": "s7", "text_en": "The little brown Luna grabbed the biggest yellow ball she found...", "text_es": "La pequeña Luna agarró la pelota amarilla más grande que encontró..."},
            {"id": "s8", "text_en": "The two little dogs celebrated the great conquest rolling...", "text_es": "Las dos perritas celebraron la gran conquista rodando..."},
            {"id": "s_outro", "text_en": "Thank you so much for watching our videos, a big kiss on your heart!", "text_es": "¡Muchas gracias por ver nuestros videos, un gran beso en tu corazón!"},
        ],
    },
    "o-que-os-cachorros-enxergam-as-cores-do": {
        "title_en": "The Colorful World of Dogs",
        "title_es": "El Mundo Colorido de los Perros",
        "secao": [
            {"id": "s_intro", "text_en": "Have you ever stopped to think if your little dog sees the world...", "text_es": "¿Alguna vez te has detenido a pensar si tu perrito ve el mundo..."},
            {"id": "s0", "text_en": "Hi little friends and little friends! How are you? It's great that you're here!", "text_es": "¡Hola, amiguitos y amiguitas! ¿Cómo están? ¡Qué bueno que estén aquí!"},
            {"id": "s1", "text_en": "Many people think dogs only see gray... But that's...", "text_es": "Mucha gente piensa que los perros solo ven gris... Pero eso..."},
            {"id": "s2", "text_en": "Because of these two cones, Fridóca sees very well the...", "text_es": "Por estos dos conos, Fridóca ve muy bien el..."},
            {"id": "s3", "text_en": "If they don't see all colors... Will they be at a disadvantage?", "text_es": "Si no ven todos los colores... ¿Será que llevan desventaja?"},
            {"id": "s4", "text_en": "And do you know why your little dog's eye shines in the dark...", "text_es": "¿Y sabes por qué el ojo de tu perrito brilla en el oscuro...?"},
            {"id": "s5", "text_en": "Another fantastic thing is how dogs perceive movement...", "text_es": "Otra cosa fantástica es cómo los perros perciben el movimiento..."},
            {"id": "s6", "text_en": "Have you noticed where Luninha's eyes are? They are more...", "text_es": "¿Ya notaste dónde están los ojos de Luninha? Están más..."},
            {"id": "s7", "text_en": "Even if the vision is not super sharp from afar... The smell...", "text_es": "Incluso si la visión no es super nítida de lejos... El olfato..."},
            {"id": "s8", "text_en": "Now that you already know this incredible secret... How about choosing...", "text_es": "Ahora que ya sabes este secreto increíble... ¿Qué tal elegir...?"},
            {"id": "s_outro", "text_en": "Thank you so much for watching our videos, a big kiss on your heart!", "text_es": "¡Muchas gracias por ver nuestros videos, un gran beso en tu corazón!"},
        ],
    },
    "passeios-seguros-como-levar-o-cachorro-p": {
        "title_en": "Adventures with Leash and Collar!",
        "title_es": "¡Aventuras con Correa y Collar!",
        "secao": [
            {"id": "s_intro", "text_en": "What if your dog's walk became a real expedition...", "text_es": "¿Y si el paseo de tu perro se convirtiera en una verdadera expedición..."},
            {"id": "s0", "text_en": "Hi little friends and little friends! How are you? It's great that you're here!", "text_es": "¡Hola, amiguitos y amiguitas! ¿Cómo están? ¡Qué bueno que estén aquí!"},
            {"id": "s1", "text_en": "In the little green square of the neighborhood... two eared friends were...", "text_es": "En la plaquita verde del barrio... dos amigas orejudas estaban..."},
            {"id": "s2", "text_en": "Frida also won a stylish collar! And the most interesting detail...", "text_es": "Frida también ganó un collar con estilo! Y el detalle más interesante..."},
            {"id": "s3", "text_en": "When arriving at the sidewalk... the sun was shining strong in the sky...", "text_es": "Al llegar a la acera... el sol brillaba fuerte en el cielo..."},
            {"id": "s4", "text_en": "Walking down the street... cars were passing making noise! The Lu...", "text_es": "Caminando por la calle... los coches pasaban haciendo ruido! La Lu..."},
            {"id": "s5", "text_en": "Suddenly... a new little friend of four legs appeared...", "text_es": "De repente... apareció un nuevo amiguito de cuatro patas..."},
            {"id": "s6", "text_en": "After so many walks... Luninha's tongue was already...", "text_es": "Después de tantas caminatas... la lengua de Luninha ya estaba..."},
            {"id": "s7", "text_en": "And we can't forget the little hygiene bag! Luna did a poop...", "text_es": "Y no podemos olvidar el saquito higiénico! Luna hizo una caca..."},
            {"id": "s8", "text_en": "Back home... with clean little paws and a heart full of gratitude...", "text_es": "De vuelta a casa... con las patitas limpias y el corazón lleno de gratitud..."},
            {"id": "s_outro", "text_en": "Thank you so much for watching our videos, a big kiss on your heart!", "text_es": "¡Muchas gracias por ver nuestros videos, un gran beso en tu corazón!"},
        ],
    },
    "por-que-cachorros-cheiram-o-bumbum-uns-d": {
        "title_en": "The Mystery of the Canine Greeting",
        "title_es": "El Misterio del Saludo Canino",
        "secao": [
            {"id": "s0", "text_en": "Hi little friends and little friends! How are you? It's great that you're here!", "text_es": "¡Hola, amiguitos y amiguitas! ¿Cómo están? ¡Qué bueno que estén aquí!"},
            {"id": "s1", "text_en": "Have you walked on the beach and seen two little dogs greeting each other?", "text_es": "¿Has paseado en la playa y visto dos perritos saludándose?"},
            {"id": "s2", "text_en": "Let's imagine our dear Luninha walking in the park! ...", "text_es": "Imaginemos a nuestra querida Luninha paseando en el parque! ..."},
            {"id": "s3", "text_en": "Suddenly, here comes Fridóca walking very calmly! The Fri...", "text_es": "¡De repente ahí viene Fridóca caminando muy tranquila! La Fri..."},
            {"id": "s4", "text_en": "But after all, why right there? Because dogs have glands...", "text_es": "Pero después de todo, ¿por qué justo ahí? Porque los perros tienen glándulas..."},
            {"id": "s5", "text_en": "By giving this quick sniff, Luninha discovers everything about...", "text_es": "Al dar este olfateo rápido, Luninha descubre todo sobre..."},
            {"id": "s6", "text_en": "After Luninha reads Fridóca's news, it's the turn of the...", "text_es": "Después de que Luninha lee las novidades de Fridóca, es el turno de..."},
            {"id": "s7", "text_en": "For us it seems funny, but dogs' brain keeps...", "text_es": "Para nosotros parece divertido, pero el cerebro de los perros guarda..."},
            {"id": "s8", "text_en": "After this complete reading of business cards, Fridóca...", "text_es": "Después de esta lectura completa de tarjetas de visita, Fridóca..."},
            {"id": "s9", "text_en": "So little friends, when you see two little dogs sniffing...", "text_es": "Entonces amiguitos, cuando vean dos perritos oliendo..."},
            {"id": "s_outro", "text_en": "Thank you so much for watching our videos, a big kiss on your heart!", "text_es": "¡Muchas gracias por ver nuestros videos, un gran beso en tu corazón!"},
        ],
    },
    "por-que-cachorros-inclinam-a-cabeca-quando-voce-fala": {
        "title_en": "Why Do Dogs Tilt Their Head?",
        "title_es": "¿Por Qué los Perros Inclinan la Cabeza?",
        "secao": [
            {"id": "s0", "text_en": "Hello, family! This is Frida and Luna's channel, with another...", "text_es": "¡Hola, familia! Este es el canal de Frida y Luna, con otro..."},
            {"id": "s1", "text_en": "Have you noticed that, out of nowhere, your dog turns his head...", "text_es": "¿Te has dado cuenta de que, de repente, tu perro gira la cabeza..."},
            {"id": "s2", "text_en": "First reason: they are true satellite dishes...", "text_es": "Primera razón: son verdaderas antenas parabólicas..."},
            {"id": "s3", "text_en": "Second reason: the long snout gets in the way of direct vision...", "text_es": "Segunda razón: el hocico largo interfiere con la visión directa..."},
            {"id": "s4", "text_en": "Third reason: they care a lot about what we do...", "text_es": "Tercera razón: les importa mucho lo que hacemos..."},
            {"id": "s4b", "text_en": "Did you know researchers did tests with several dogs...", "text_es": "¿Sabías que investigadores hicieron pruebas con varios perros..."},
            {"id": "s5", "text_en": "And of course there's the human's reaction factor too! Hahaha! The...", "text_es": "Y claro que también hay el factor de reacción del humano! ¡Jeje! El..."},
            {"id": "s6", "text_en": "So next time your furry tortures the little head...", "text_es": "Entonces la próxima vez que tu peludo torture la cabecita..."},
        ],
    },
    "por-que-o-cachorro-gira-antes-de-dei-98ff": {
        "title_en": "Why Do Dogs Spin Before Lying Down?",
        "title_es": "¿Por Qué los Perros Dan Vueltas Antes de Acostarse?",
        "secao": [
            {"id": "s1", "text_en": "Help! Luna decided that the plush bed is a pizza...", "text_es": "¡Ayuda! Luna decidió que la cama de felpa es una pizza..."},
            {"id": "s2", "text_en": "Luna stops, takes a deep breath and announces with all the enthusiasm of...", "text_es": "Luna se detiene, respira hondo y anuncia con todo el entusiasmo de..."},
            {"id": "s3", "text_en": "Let's go back in time, long before the cozy sofas and the kibble...", "text_es": "Regresemos en el tiempo, mucho antes de los sofás cómodos y la comida..."},
            {"id": "s4", "text_en": "Imagine the scene: tall grass, cold wind blowing on the ears...", "text_es": "Imagina la escena: hierba alta, viento frío soplando en las orejas..."},
            {"id": "s4b", "text_en": "Frida raises an eyelid with supreme effort and grumbles:...", "text_es": "Frida levanta un párpado con esfuerzo supremo y refunfuña:..."},
            {"id": "s5", "text_en": "But wait, the story gets even more interesting and full of...", "text_es": "Pero espera, la historia se pone aún más interesante y llena de..."},
            {"id": "s6", "text_en": "Luna tries to apply this technique on grandma's pillow and almost...", "text_es": "Luna intenta aplicar esta técnica en la almohada de la abuela y casi..."},
            {"id": "s7", "text_en": "Hold on tight because there's one more scientific secret...", "text_es": "Agárrense fuerte porque hay un secreto científico más..."},
            {"id": "s8", "text_en": "And it doesn't stop there, because the little furry body needs to manage...", "text_es": "Y no termina ahí, porque el cuerpecito peludo necesita gestionar..."},
            {"id": "s8b", "text_en": "Frida lets out a deep sigh, finally decides to settle...", "text_es": "Frida suelta un suspiro profundo, finalmente decide acomodarse..."},
            {"id": "s9", "text_en": "See how many interesting things fit inside a simple...", "text_es": "Mira cuántas cosas interesantes caben dentro de una simple..."},
            {"id": "s10", "text_en": "If you also have a real spinning hurricane in your house...", "text_es": "Si también tienes un verdadero huracán giratorio en tu casa..."},
        ],
    },
    "por-que-o-cachorro-lambe-o-seu-rosto": {
        "title_en": "Why Does the Dog Lick Your Face?",
        "title_es": "¿Por Qué el Perro Lame Tu Cara?",
        "secao": [
            {"id": "s0", "text_en": "Hi little friend! How are you? Great to see you here!", "text_es": "¡Hola, amiguito! ¿Cómo estás? ¡Qué bueno verte aquí!"},
            {"id": "s1", "text_en": "Have you ever received a lick right in the middle of your nose? It's wet, it's...", "text_es": "¿Alguna vez has recibido una lamida justo en medio de tu nariz? Está mojada, está..."},
            {"id": "s2", "text_en": "Your face is like a book full of stories for your dog...", "text_es": "Tu cara es como un libro lleno de historias para tu perro..."},
            {"id": "s3", "text_en": "The most beautiful reason of all is love! For dogs, licking...", "text_es": "La razón más hermosa de todas es el amor! Para los perros, lamer..."},
            {"id": "s4", "text_en": "Since very little, puppies lick their mother's face...", "text_es": "Desde muy pequeños, los cachorros lamen la cara de su madre..."},
            {"id": "s5", "text_en": "Do you know something very fun? Our skin has a taste...", "text_es": "¿Sabes algo muy divertido? Nuestra piel tiene un sabor..."},
            {"id": "s6", "text_en": "Sometimes the lick is just a little affectionate message saying: hey...", "text_es": "A veces la lamida es solo un mensajito cariñoso diciendo: ei..."},
            {"id": "s7", "text_en": "When the little dog gives you a lick, his brain releases...", "text_es": "Cuando el perrito te da una lamida, su cerebro libera..."},
            {"id": "s8", "text_en": "So next time you receive a wet lick...", "text_es": "Entonces la próxima vez que recibas una lamida mojada..."},
            {"id": "s_outro", "text_en": "Thank you so much for watching our videos, a big kiss on your heart!", "text_es": "¡Muchas gracias por ver nuestros videos, un gran beso en tu corazón!"},
        ],
    },
    "por-que-o-cachorro-uiva-quando-ouve-uma": {
        "title_en": "The Mystery of the Singing Siren",
        "title_es": "El Misterio de la Sirena Cantora",
        "secao": [
            {"id": "s_intro", "text_en": "Have you seen a dog lift its snout and howl very loud...", "text_es": "¿Has visto a un perro levantar el hocico y aullar muy fuerte..."},
            {"id": "s0", "text_en": "Hi little friends and little friends! How are you? It's great that you're here!", "text_es": "¡Hola, amiguitos y amiguitas! ¿Cómo están? ¡Qué bueno que estén aquí!"},
            {"id": "s1", "text_en": "Everything was very quiet in Fridóca and Luninha's yard...", "text_es": "Todo estaba muy tranquilo en el patio de Fridóca y Luninha..."},
            {"id": "s2", "text_en": "It was the firefighters' car passing at full speed out there...", "text_es": "Era el coche de los bomberos pasando a toda velocidad afuera..."},
            {"id": "s3", "text_en": "Luninha couldn't take it! She threw her head back, pointing...", "text_es": "Luninha no aguantó! Echó la cabeza hacia atrás, señalando..."},
            {"id": "s4", "text_en": "For Luninha, that giant siren was a very big dog...", "text_es": "Para Luninha, esa sirena gigante era un perro muy grande..."},
            {"id": "s5", "text_en": "Fridóca thought that singing was very lively and decided to join in...", "text_es": "Fridóca pensó que ese canto era muy animado y decidió participar..."},
            {"id": "s6", "text_en": "Many people think the siren hurts the dog's ear...", "text_es": "Mucha gente piensa que la sirena duele el oído del perro..."},
            {"id": "s7", "text_en": "Little by little, the truck was turning the corner and the sound of...", "text_es": "Poco a poco, el camión doblaba la esquina y el sonido de..."},
            {"id": "s8", "text_en": "The two looked at each other super proud! Luninha thought that...", "text_es": "Las dos se miraron super orgullosas! Luninha pensaba que..."},
            {"id": "s_outro", "text_en": "Thank you so much for watching our videos, a big kiss on your heart!", "text_es": "¡Muchas gracias por ver nuestros videos, un gran beso en tu corazón!"},
        ],
    },
    "saga-do-osso-de-ouro-24-a-floresta-do-qu": {
        "title_en": "Frida and Luna: The Backyard Forest",
        "title_es": "Frida y Luna: El Bosque del Patio",
        "secao": [
            {"id": "s0", "text_en": "Hi little friend! How are you? Great to see you here!", "text_es": "¡Hola, amiguito! ¿Cómo estás? ¡Qué bueno verte aquí!"},
            {"id": "s1", "text_en": "The Golden Bone map pointed to a mysterious place...", "text_es": "El mapa del Hueso de Oro señalaba un lugar misterioso..."},
            {"id": "s2", "text_en": "Frida took the first step with her chubby paws. The grass...", "text_es": "Frida dio el primer paso con sus patitas gorditas. El pasto..."},
            {"id": "s3", "text_en": "Suddenly, a giant shadow appeared among the ferns! ...", "text_es": "¡De repente apareció una sombra gigante entre los helechos! ..."},
            {"id": "s4", "text_en": "Further ahead, a giant obstacle blocked the path...", "text_es": "Más adelante, un obstáculo gigante bloqueaba el camino..."},
            {"id": "s5", "text_en": "Continuing the mission, Luninha found something shining near...", "text_es": "Continuando la misión, Luninha encontró algo brillando cerca..."},
            {"id": "s6", "text_en": "Suddenly, strange noises started coming from above the...", "text_es": "De repente, ruidos extraños empezaron a venir de arriba del..."},
            {"id": "s7", "text_en": "To get to the center of the forest, they needed to cross...", "text_es": "Para llegar al centro del bosque, necesitaban cruzar..."},
            {"id": "s8", "text_en": "With their whole bodies covered in dirt, they finally arrived...", "text_es": "Con todo el cuerpo cubierto de tierra, finalmente llegaron..."},
            {"id": "s_outro", "text_en": "Thank you so much for watching our videos, a big kiss on your heart!", "text_es": "¡Muchas gracias por ver nuestros videos, un gran beso en tu corazón!"},
        ],
    },
    "saga-do-osso-de-ouro-34-o-guardiao-do-te": {
        "title_en": "The Guardian of the Golden Bone",
        "title_es": "El Guardián del Hueso de Oro",
        "secao": [
            {"id": "s0", "text_en": "Hi little friends and little friends! How are you? It's great that you're here!", "text_es": "¡Hola, amiguitos y amiguitas! ¿Cómo están? ¡Qué bueno que estén aquí!"},
            {"id": "s1", "text_en": "The treasure hunt continues! The brave bulldog Frida, our...", "text_es": "¡La búsqueda del tesoro continúa! La valiente bulldog Frida, nuestra..."},
            {"id": "s2", "text_en": "Suddenly, Luninha's pointy ears stood up! A...", "text_es": "¡De repente las orejas puntiagudas de Luninha se levantaron! Un..."},
            {"id": "s3", "text_en": "Behold! The powerful guardian of the treasure appears! A furry being...", "text_es": "¡He aquí que aparece el poderoso guardián del tesoro! Un ser peludo..."},
            {"id": "s4", "text_en": "No one passes the guardian without solving my royal riddle! You...", "text_es": "¡Nadie pasa al guardián sin resolver mi acertijo real! Tú..."},
            {"id": "s5", "text_en": "Luninha stepped forward to show her skills! ...", "text_es": "Luninha dio un paso al frente para mostrar sus habilidades! ..."},
            {"id": "s6", "text_en": "Now it was our dear Fridóca's turn to try! The bulldog...", "text_es": "Ahora era el turno de nuestra querida Fridóca de intentar! La bulldog..."},
            {"id": "s7", "text_en": "In the excitement of the number, Fridóca took a jump a little more...", "text_es": "En la emoción del número, Fridóca dio un salto un poco más..."},
            {"id": "s8", "text_en": "The guardian fell into laughter, laughing until rolling on the grass! You...", "text_es": "El guardián cayó en la risa, riendo hasta rodar por el pasto! Ustedes..."},
            {"id": "s9", "text_en": "Inside the sparkling box was it... The shiny Golden Bone...", "text_es": "Dentro de la caja centelleante estaba... El reluciente Hueso de Oro..."},
            {"id": "s_outro", "text_en": "Thank you so much for watching our videos, a big kiss on your heart!", "text_es": "¡Muchas gracias por ver nuestros videos, un gran beso en tu corazón!"},
        ],
    },
    "teste-10s-dentes-cachorro": {
        "title_en": "Cleaning the Dog's Teeth",
        "title_es": "Limpiando los Dientes del Perro",
        "secao": [
            {"id": "s1", "text_en": "Cleaning the dog's teeth is simpler than it seems: use...", "text_es": "Limpiar los dientes del perro es más simple de lo que parece: usa..."},
        ],
    },
    "teste-gemini-1min": {
        "title_en": "Hide and Seek in the Rain",
        "title_es": "Escondite bajo la Lluvia",
        "secao": [
            {"id": "s_intro", "text_en": "Have you tried playing hide and seek in the garden exactly...", "text_es": "¿Has intentado jugar al escondite en el jardín exactamente..."},
            {"id": "s0", "text_en": "Oiê, galerinha animada! Que alegria ter vocês aqui no nosso ...", "text_es": "¡Oiê, galerinha animada! Qué alegría tenerlos aquí en nuestro ..."},
            {"id": "s1", "text_en": "The gray sky started to drizzle right at playtime! ...", "text_es": "El cielo gris empezó a lloviznar justo a la hora de jugar! ..."},
            {"id": "s2", "text_en": "Ten! There goes Fridóca looking for her little sister sausage! She looked...", "text_es": "¡Diez! ¡Allí va Fridóca buscando a su hermanita salchicha! Miró..."},
            {"id": "s3", "text_en": "Luninha was well hidden under the big leaves of the...", "text_es": "Luninha estaba bien escondida debajo de las hojas grandes del..."},
            {"id": "s4", "text_en": "Now it was Luninha's turn to count to ten! Fridóca ran...", "text_es": "Ahora era el turno de Luninha de contar hasta diez! Fridóca corrió..."},
            {"id": "s5", "text_en": "Luninha opened her eyes and heard the noise of the bucket rolling! ...", "text_es": "Luninha abrió los ojos y escuchó el ruido del balde rodando! ..."},
            {"id": "s6", "text_en": "The hide and seek game became a big party in the...", "text_es": "El juego de escondite se convirtió en una gran fiesta en el..."},
            {"id": "s7", "text_en": "Luninha saw the biggest puddle of water in the garden right in the...", "text_es": "Luninha vio el charco de agua más grande del jardín justo en el..."},
            {"id": "s8", "text_en": "After hiding a thousand times, the two walked to the...", "text_es": "Después de esconderse mil veces, las dos caminaron hasta el..."},
            {"id": "s_final", "text_en": "And that's how today's wet adventure ends! This is the end...", "text_es": "Y así termina nuestra aventura mojada de hoy! Este es el fin..."},
            {"id": "s_outro", "text_en": "Thank you so much for watching until the end! If you liked this...", "text_es": "¡Muchas gracias por ver hasta el final! Si te gustó esto..."},
        ],
    },
    "um-dia-na-vida-de-um-cachorro-do-ponto-d": {
        "title_en": "Rex's Incredible Day",
        "title_es": "El Increíble Día de Rex",
        "secao": [
            {"id": "s0", "text_en": "Hi little friend! How are you? Great to see you here!", "text_es": "¡Hola, amiguito! ¿Cómo estás? ¡Qué bueno verte aquí!"},
            {"id": "s1", "text_en": "The sun didn't even come out right and my nose already feels everything! There's a smell...", "text_es": "El sol ni siquiera salió bien y mi nariz ya lo siente todo! Hay olor..."},
            {"id": "s2", "text_en": "The most sacred moment of the day arrived! The sound of the grains...", "text_es": "El momento más sagrado del día llegó! El sonido de los granos..."},
            {"id": "s3", "text_en": "Time to work! I assume my official post at the living room window...", "text_es": "Hora de trabajar! Asumo mi puesto oficial en la ventana de la sala..."},
            {"id": "s4", "text_en": "Suddenly, horror happens! The human grabs that monster...", "text_es": "¡De repente sucede el horror! El humano agarra ese monstruo..."},
            {"id": "s5", "text_en": "The human grabs a colorful ribbon with a hook and says the word...", "text_es": "El humano agarra una cinta de colores con un gancho y dice la palabra..."},
            {"id": "s6", "text_en": "The street is full of mysteries! I smell this tree... I smell here...", "text_es": "La calle está llena de misterios! Huelo este árbol... huelo aquí..."},
            {"id": "s7", "text_en": "In the park, I see the legendary Vira-Lata Caramelo! He runs sup...", "text_es": "En el parque, veo al legendario Vira-Lata Caramelo! Él corre sup..."},
            {"id": "s8", "text_en": "I go back home tired of so much adventure. It's time to rest...", "text_es": "Vuelvo a casa cansado de tanta aventura. Es hora de descansar..."},
            {"id": "s9", "text_en": "I wake up with the smell of the humans' dinner! I stay right by...", "text_es": "Me despierto con el olor de la cena de los humanos! Me quedo justo al..."},
            {"id": "s10", "text_en": "The night arrives and the house gets very calm. I go up to my little bed...", "text_es": "Llega la noche y la casa se pone muy tranquila. Subo a mi camita..."},
            {"id": "s_outro", "text_en": "Thank you so much for watching our videos, a big kiss on your heart!", "text_es": "¡Muchas gracias por ver nuestros videos, un gran beso en tu corazón!"},
        ],
    },
    "video-educativo-sobre-banho-em-cachorro": {
        "title_en": "The Incredible Canine Bath Odyssey: Save Yourself Who Can!",
        "title_es": "La Increíble Odisea del Baño Canino: ¡Sálvese Quien Pueda!",
        "secao": [
            {"id": "s1", "text_en": "Hey gang! Who here has ever tried to bathe a dog and...", "text_es": "Oye pandilla animal! ¿Quién aquí ha intentado bañar a un perro y...?"},
            {"id": "s2", "text_en": "First step, my friends: planning! It's useless to just open...", "text_es": "Primer paso, mis amigos: planeamiento! No sirve de nada solo abrir..."},
            {"id": "s3", "text_en": "Time to take the little dog to the bathroom. This is where the magic...", "text_es": "Hora de llevar al perrito al baño. Aquí es donde ocurre la magia..."},
            {"id": "s4", "text_en": "Maximum attention here, folks! No freezing water for...", "text_es": "Máxima atención aquí, gente! Nada de agua congelante para..."},
            {"id": "s4b", "text_en": "It's time for the truth! Start by wetting the little paws of...", "text_es": "¡Es hora de la verdad! Empieza mojando las patitas de..."},
            {"id": "s5", "text_en": "Shampoo time! Spread the product with circular massages...", "text_es": "¡Hora del shampoo! Extiende el producto con masajes circulares..."},
            {"id": "s6", "text_en": "Now remove all the soap with clean water, making sure not to...", "text_es": "Ahora retira todo el jabón con agua limpia, asegurándote de no..."},
            {"id": "s7", "text_en": "Red alert, folks! At any second, it's going to happen...", "text_es": "¡Alerta roja, gente! En cualquier segundo va a suceder..."},
            {"id": "s8", "text_en": "With the help of a soft towel, remove the excess water doing...", "text_es": "Con la ayuda de una toalla suave, retira el exceso de agua haciendo..."},
            {"id": "s8b", "text_en": "To finish with a flourish, it's time to brush the fur and...", "text_es": "Para finalizar con broche de oro, es hora de cepillar el pelo y..."},
            {"id": "s9", "text_en": "Mission accomplished with absolute success, team! Time to give...", "text_es": "¡Misión cumplida con éxito absoluto, equipo! Hora de dar..."},
            {"id": "s10", "text_en": "Always remember that the bath should be a moment of cari...", "text_es": "Recuerden siempre que el baño debe ser un momento de cari..."},
        ],
    },
    "video-engracado-sobre-buldogue-ingles-00": {
        "title_en": "The Definitive Guide to the English Bulldog: Caught, Snoring and Lots of Cuteness!",
        "title_es": "¡La Guía Definitiva del Bulldog Inglés: Atrapados, Ronquidos y Mucha Ternura!",
        "secao": [
            {"id": "s1", "text_en": "Hey animal gang! Have you ever wondered what it would be like to live...", "text_es": "Oye pandilla animal! ¿Se han preguntado cómo sería vivir..."},
            {"id": "s2", "text_en": "But look, not everything was always glamour and sophistication in life...", "text_es": "Pero mira, no todo fue siempre glamour y sofisticación en la vida..."},
            {"id": "s3", "text_en": "Talking about energy... or the lack of it... The favorite sport...", "text_es": "Hablando de energía... o la falta de ella... El deporte favorito..."},
            {"id": "s4", "text_en": "And get the ear protectors ready, because when night comes...", "text_es": "Y preparen los protectores de oídos, porque cuando llega la noche..."},
            {"id": "s4b", "text_en": "Another very strong point of this breed is the dramatic skill...", "text_es": "Otro punto muy fuerte de esta raza es la habilidad dramática..."},
            {"id": "s5", "text_en": "Now let's talk about maintenance, because being fancy requires work...", "text_es": "Ahora hablemos de mantenimiento, porque ser elegante requiere trabajo..."},
            {"id": "s6", "text_en": "And a lot of attention to the thermometer, folks! As they have the snout...", "text_es": "Y mucha atención al termómetro, gente! Como tienen el hocico..."},
            {"id": "s7", "text_en": "Another very important detail is their relationship with food...", "text_es": "Otro detalle muy importante es su relación con la comida..."},
            {"id": "s8", "text_en": "Despite this brave little face that doesn't scare even a fly,...", "text_es": "A pesar de esta carita brava que no asusta ni siquiera a una mosca,..."},
            {"id": "s8b", "text_en": "Of course all this charm requires a regular check-up with the vet...", "text_es": "Claro que todo este encanto requiere un chequeo regular con el veterinario..."},
            {"id": "s9", "text_en": "Summing up, having an English Bulldog is signing a lifetime contract...", "text_es": "Resumiendo, tener un Bulldog Inglés es firmar un contrato de por vida..."},
            {"id": "s10", "text_en": "And did you like knowing the funniest secrets of this breed...", "text_es": "Y ¿les gustó conocer los secretos más divertidos de esta raza..."},
        ],
    },
    "video-engracado-sobre-buldogue-ingles-divertido": {
        "title_en": "The English Bulldog: The Laziest, Snoring and Funniest Dog in the World!",
        "title_es": "El Bulldog Inglés: El Perro Más Perezoso, Roncador y Divertido del Mundo!",
        "secao": [
            {"id": "s1", "text_en": "Hey folks! Have you ever stopped to look at an English Bulldog and thought...", "text_es": "Oye, gente! ¿Alguna vez te has detenido a mirar un Bulldog Inglés y pensaste..."},
            {"id": "s2", "text_en": "You know those wrinkles that look like a crumpled treasure map? ...", "text_es": "¿Sabes esas arrugas que parecen un mapa del tesoro arrugado? ..."},
            {"id": "s3", "text_en": "The English Bulldog's favorite sport is the world championship...", "text_es": "El deporte favorito del Bulldog Inglés es el campeonato mundial..."},
            {"id": "s4", "text_en": "If laziness were the Olympics, the Bulldog would take gold, silver...", "text_es": "Si la pereza fuera la olimpiada, el Bulldog se llevaría oro, plata..."},
            {"id": "s5", "text_en": "The English Bulldog sleeps anywhere, any time, any...", "text_es": "El Bulldog Inglés duerme en cualquier lugar, a cualquier hora, en..."},
            {"id": "s6", "text_en": "Get the ear protectors ready! When night comes, the snor...", "text_es": "¡Prepara los protectores de oídos! Cuando llega la noche, el ronc..."},
            {"id": "s7", "text_en": "Besides snoring, they make strange noises: grumbles, grunts,...", "text_es": "Además del ronquido, hacen ruidos extraños: resmungos, gruñidos..."},
            {"id": "s8", "text_en": "With this short snout, the Bulldog's internal air conditioning...", "text_es": "Con este hocico corto, el aire acondicionado interno del Bulldog..."},
            {"id": "s9", "text_en": "Being fancy requires work! These adorable little folds on the face...", "text_es": "Ser elegante requiere trabajo! Esos adorables pliegues en la cara..."},
            {"id": "s10", "text_en": "All this charm requires a regular check-up with the vet...", "text_es": "Todo este encanto requiere un chequeo regular con el veterinario..."},
            {"id": "s11", "text_en": "Despite this brave little face that doesn't scare even a fly,...", "text_es": "A pesar de esta carita brava que no asusta ni siquiera a una mosca..."},
            {"id": "s12", "text_en": "They are great companions as long as children understand...", "text_es": "Son excelentes compañeros mientras los niños entiendan..."},
            {"id": "s13", "text_en": "Another very important detail: their relationship with food...", "text_es": "Otro detalle muy importante: su relación con la comida..."},
            {"id": "s14", "text_en": "Why does everyone love an English Bulldog? Because they are...", "text_es": "¿Por qué todos aman a un Bulldog Inglés? Porque son..."},
            {"id": "s15", "text_en": "Summing up: having an English Bulldog is signing a lifetime...", "text_es": "Resumiendo: tener un Bulldog Inglés es firmar un contrato de por vida..."},
            {"id": "s16", "text_en": "And did you like knowing the hilarious secrets of this breed...", "text_es": "Y ¿les gustó conocer los secretos más divertidos de esta raza..."},
        ],
    },
    "vira-lata-caramelo-o-heroi-do-brasil": {
        "title_en": "The Incredible Hero Caramelo",
        "title_es": "El Increíble Héroe Caramelo",
        "secao": [
            {"id": "s_intro", "text_en": "What if the greatest superhero of all didn't wear a cape, but had...", "text_es": "¿Y si el superhéroe más grande de todos no usara capa, sino que tuviera..."},
            {"id": "s0", "text_en": "Hi little friends and little friends! How are you? It's great that you're here!", "text_es": "¡Hola, amiguitos y amiguitas! ¿Cómo están? ¡Qué bueno que estén aquí!"},
            {"id": "s1", "text_en": "In a very lively little town, lived a little dog called...", "text_es": "En un pueblito muy animado, vivía un perrito llamado..."},
            {"id": "s2", "text_en": "Every morning, Pipo woke up very early with a very mission...", "text_es": "Todas las mañanas, Pipo se despertaba muy temprano con una misión muy..."},
            {"id": "s3", "text_en": "But on a beautiful sunny day, something very unexpected happened...", "text_es": "Pero un hermoso día soleado, algo muy inesperado sucedió..."},
            {"id": "s4", "text_en": "It's at that moment that our hero springs into action! Pipo gave a...", "text_es": "Es en ese momento que nuestro héroe entra en acción! Pipo dio un..."},
            {"id": "s5", "text_en": "The birds in the sky even flapped their wings with joy! Pipo delivered...", "text_es": "Los pájaros en el cielo incluso agitaron las alas de alegría! Pipo entregó..."},
            {"id": "s6", "text_en": "Pipo used his super speed and put the little paw in place...", "text_es": "Pipo usó su súper velocidad y puso la paticita en su lugar..."},
            {"id": "s7", "text_en": "At the end of the afternoon, the whole square gathered to celebrate! ...", "text_es": "Al final de la tarde, toda la plaza se reunió para celebrar! ..."},
            {"id": "s_outro", "text_en": "Thank you so much for watching our videos, a big kiss on your heart!", "text_es": "¡Muchas gracias por ver nuestros videos, un gran beso en tu corazón!"},
        ],
    },
    "bulldogue-ingles-frida-e-dachshund-marro": {
        "title_en": "English Bulldog and Dachshund Marrom",
        "title_es": "Bulldog Inglés y Teckel Marrón",
        "secao": [],
    },
    "e-se-os-cachorros-pudessem-falar-por-um": {
        "title_en": "What If Dogs Could Talk?",
        "title_es": "¿Y Si los Perros Pudieran Hablar?",
        "secao": [],
    },
    "golden-retriever-por-que-ele-e-o-melhor": {
        "title_en": "Golden Retriever: Why He's the Best",
        "title_es": "Golden Retriever: ¿Por Qué Es el Mejor?",
        "secao": [],
    },
}


def _secao(secoes_pt, sid, texto_en, texto_es):
    """Retorna dict com id + texto traduzido, ou None se nao houver traducao."""
    if not texto_en and not texto_es:
        return None
    return {"id": sid, "text_en": texto_en, "text_es": texto_es}


def montar_traducao(script_pt, trad):
    """Copia script pt e sobrescreve title + textos traduzidos."""
    out_en = json.loads(json.dumps(script_pt, ensure_ascii=False))
    out_es = json.loads(json.dumps(script_pt, ensure_ascii=False))
    out_en["title"] = trad.get("title_en", script_pt.get("title", ""))
    out_es["title"] = trad.get("title_es", script_pt.get("title", ""))
    por_id = {s.get("id"): s for s in script_pt.get("sections", [])}
    for t in trad.get("secao", []):
        sid = t["id"]
        if sid in por_id:
            base = por_id[sid]
            en_sec = dict(base); en_sec["text"] = t.get("text_en", base.get("text", ""))
            es_sec = dict(base); es_sec["text"] = t.get("text_es", base.get("text", ""))
            # substitui na lista
            out_en["sections"] = [en_sec if s.get("id") == sid else s for s in out_en["sections"]]
            out_es["sections"] = [es_sec if s.get("id") == sid else s for s in out_es["sections"]]
    return out_en, out_es


def main():
    ap = __import__("argparse").ArgumentParser()
    ap.add_argument("--only", help="slug de um projeto específico")
    ap.add_argument("--force", action="store_true", help="regenera mesmo se ja existir")
    args = ap.parse_args()

    projetos = sorted([d for d in os.listdir(BASE) if (BASE / d).is_dir()])
    gerados = 0
    for pname in projetos:
        if args.only and pname != args.only:
            continue
        proj = BASE / pname
        art = proj / "artifacts"
        script_pt = art / "script.json"
        if not script_pt.exists():
            print("PULADO %s: sem script.json" % pname, flush=True)
            continue
        script = json.load(open(script_pt, encoding="utf-8"))

        trad = TRADUCOES.get(pname)
        if not trad:
            print("PULADO %s: sem traducao cadastrada" % pname, flush=True)
            continue

        out_en, out_es = montar_traducao(script, trad)

        for lang, out in (("en", out_en), ("es", out_es)):
            out_path = art / ("script_%s.json" % lang)
            if out_path.exists() and not args.force:
                print("JA EXISTE %s/%s" % (pname, lang), flush=True)
                continue
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, indent=2)
            print("GERADO %s/%s (%d secoes)" % (pname, lang, len(out["sections"])), flush=True)
            gerados += 1

    print("\nTotal gerado: %d" % gerados, flush=True)


if __name__ == "__main__":
    main()
