import {
  Edit2, Film, Image as ImageIcon, RotateCw, Mic, HardDrive,
  Zap, Layout, Clipboard, Download,
} from "lucide-react";

const PHASES = [
  { key: "script", label: "Roteiro", sub: "IA web - Gemini", icon: Edit2 },
  { key: "scenes", label: "Cenas", sub: "IA - HTML", icon: Film },
  { key: "images", label: "Imagens", sub: "Gemini WEB", icon: ImageIcon },
  { key: "music", label: "Música", sub: "Procedural", icon: RotateCw },
  { key: "narration", label: "Narração", sub: "Edge-TTS local", icon: Mic },
  { key: "timeline", label: "Timeline", sub: "Linha do tempo", icon: HardDrive },
  { key: "mix", label: "Mixagem", sub: "Áudio final", icon: Zap },
  { key: "compose", label: "Composição", sub: "HyperFrames", icon: Layout },
  { key: "preprocess", label: "Pré-proc.", sub: "Imagens", icon: Clipboard },
  { key: "render", label: "Render", sub: "MP4 final", icon: Download },
];

const PHASE_KEYS = PHASES.map(p => p.key);
const PHASE_NAME = Object.fromEntries(PHASES.map(p => [p.key, p.label]));

export { PHASES, PHASE_KEYS, PHASE_NAME };
