#!/bin/bash
# Drives POST /repair once per morph type against a running gpu_worker server,
# saving each result as out_<morph_type>.png next to this script's caller.
#
# Usage:
#   ./scripts/generate_morph_variations.sh [image_path] [output_dir] [morph_type ...]
#
# Examples:
#   ./scripts/generate_morph_variations.sh
#   ./scripts/generate_morph_variations.sh test_photos/photo2.jpg
#   ./scripts/generate_morph_variations.sh test_photos/photo1.jpg out beard smile
set -euo pipefail

HOST="${GPU_WORKER_HOST:-http://localhost:8000}"
IMAGE="${1:-test_photos/photo1.jpg}"
OUTPUT_DIR="${2:-.}"
EXTRA_ARGS=("${@:3}")

SEED=42
GUIDANCE_SCALE=6
NUM_INFERENCE_STEPS=30
NEGATIVE_PROMPT="blurry, distorted face, deformed, extra limbs, low quality, artifacts, wrong identity"

# --- Morph type constants -----------------------------------------------
# Every morph type must have a matching entry in PROMPTS and STRENGTHS.
MORPH_TYPES=(aging angle beard hairstyle smile)

declare -A PROMPTS=(
  [aging]="high quality portrait of the same person aged 30 years older, visible wrinkles, gray and white hair, age spots, same pose and composition, preserve identity"
  [angle]="high quality portrait of the same person from a slightly different three-quarter angle, natural skin, preserve identity, same lighting and composition"
  [beard]="high quality portrait of the same person with a full grown beard and mustache, natural skin, preserve identity and pose, same composition"
  [hairstyle]="high quality portrait of the same person with a completely different modern hairstyle, natural skin, preserve identity and pose, same composition"
  [smile]="high quality portrait of the same person smiling broadly with visible teeth, natural skin, preserve identity and pose, same composition"
)

# Pushed above the 0.2-0.3 repair-strength range so the visual change is
# actually visible; still capped below ~0.7 to keep identity recognizable.
declare -A STRENGTHS=(
  [aging]=0.6
  [angle]=0.55
  [beard]=0.6
  [hairstyle]=0.65
  [smile]=0.5
)
# --------------------------------------------------------------------------

run_variant() {
  local morph_type="$1"
  local prompt="${PROMPTS[$morph_type]}"
  local strength="${STRENGTHS[$morph_type]}"
  local out_file="${OUTPUT_DIR}/out_${morph_type}.png"

  echo "=== ${morph_type} (strength=${strength}) ==="
  curl -s -X POST "${HOST}/repair" \
    -H "X-Request-Id: variant-${morph_type}" \
    -F "image=@${IMAGE}" \
    -F "prompt=${prompt}" \
    -F "negative_prompt=${NEGATIVE_PROMPT}" \
    -F "seed=${SEED}" \
    -F "strength=${strength}" \
    -F "guidance_scale=${GUIDANCE_SCALE}" \
    -F "num_inference_steps=${NUM_INFERENCE_STEPS}" \
    | python -c "
import sys, json, base64
d = json.load(sys.stdin)
if d.get('success'):
    open('${out_file}', 'wb').write(base64.b64decode(d['data']['image_base64']))
    print('saved ${out_file}, duration_ms=', d['data']['duration_ms'])
else:
    print('FAILED:', d.get('error'))
    sys.exit(1)
"
}

selected_types=("${EXTRA_ARGS[@]}")
if [ "${#selected_types[@]}" -eq 0 ]; then
  selected_types=("${MORPH_TYPES[@]}")
fi

mkdir -p "${OUTPUT_DIR}"

for morph_type in "${selected_types[@]}"; do
  if [ -z "${PROMPTS[$morph_type]+x}" ]; then
    echo "Unknown morph type '${morph_type}'. Known types: ${MORPH_TYPES[*]}" >&2
    exit 1
  fi
  run_variant "$morph_type"
done

echo "=== done ==="
