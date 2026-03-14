/**
 * Run fal.ai SAM 3D on furniture images in Input_Picture,
 * save .ply and .glb per image into Output_Modeling/<image_name>/
 * Requires: FAL_KEY (env or .env)
 */

import "dotenv/config";
import { fal } from "@fal-ai/client";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const INPUT_DIR = path.join(__dirname, "Input_Picture");
// 결과 .ply/.glb 파일은 Output_Modeling 폴더에 저장
const OUTPUT_DIR = path.join(__dirname, "Output_Modeling");
const IMAGE_EXT = [".png", ".jpg", ".jpeg", ".webp"];

async function downloadToFile(url, filePath) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Download failed: ${res.status} ${url}`);
  const buffer = Buffer.from(await res.arrayBuffer());
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  fs.writeFileSync(filePath, buffer);
}

function getImageFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => {
    const ext = path.extname(f).toLowerCase();
    return IMAGE_EXT.includes(ext);
  });
}

async function processImage(imageName) {
  const imagePath = path.join(INPUT_DIR, imageName);
  const baseName = path.basename(imageName, path.extname(imageName));
  const outFolder = OUTPUT_DIR;

  console.log(`[${imageName}] Uploading...`);
  const buffer = fs.readFileSync(imagePath);
  const file = new File([buffer], imageName, { type: "image/png" });
  const imageUrl = await fal.storage.upload(file);
  console.log(`[${imageName}] Running SAM 3D...`);

  const result = await fal.subscribe("fal-ai/sam-3/3d-objects", {
    input: {
      image_url: imageUrl,
      prompt: "furniture",
    },
    logs: true,
    onQueueUpdate: (update) => {
      if (update.status === "IN_PROGRESS" && update.logs) {
        update.logs.forEach((log) => console.log("  ", log.message));
      }
    },
  });

  const data = result.data;
  fs.mkdirSync(outFolder, { recursive: true });

  if (data.gaussian_splat?.url) {
    const plyPath = path.join(outFolder, `${baseName}.ply`);
    await downloadToFile(data.gaussian_splat.url, plyPath);
    console.log(`[${imageName}] Saved: ${plyPath}`);
  }
  if (data.model_glb?.url) {
    const glbPath = path.join(outFolder, `${baseName}.glb`);
    await downloadToFile(data.model_glb.url, glbPath);
    console.log(`[${imageName}] Saved: ${glbPath}`);
  }
  if (data.individual_splats?.length) {
    for (let i = 0; i < data.individual_splats.length; i++) {
      const url = data.individual_splats[i]?.url;
      if (url) {
        const p = path.join(outFolder, `${baseName}_object_${i}.ply`);
        await downloadToFile(url, p);
        console.log(`[${imageName}] Saved: ${p}`);
      }
    }
  }
  if (data.individual_glbs?.length) {
    for (let i = 0; i < data.individual_glbs.length; i++) {
      const url = data.individual_glbs[i]?.url;
      if (url) {
        const p = path.join(outFolder, `${baseName}_object_${i}.glb`);
        await downloadToFile(url, p);
        console.log(`[${imageName}] Saved: ${p}`);
      }
    }
  }
  if (data.artifacts_zip?.url) {
    const zipPath = path.join(outFolder, `${baseName}_artifacts.zip`);
    await downloadToFile(data.artifacts_zip.url, zipPath);
    console.log(`[${imageName}] Saved: ${zipPath}`);
  }

  return outFolder;
}

async function main() {
  if (!process.env.FAL_KEY) {
    console.error("Set FAL_KEY environment variable (fal.ai API key).");
    process.exit(1);
  }

  const images = getImageFiles(INPUT_DIR);
  if (images.length === 0) {
    console.log("No images found in", INPUT_DIR);
    return;
  }

  console.log("Found", images.length, "image(s). Output:", OUTPUT_DIR);
  for (const name of images) {
    try {
      await processImage(name);
    } catch (e) {
      console.error(`Error processing ${name}:`, e.message);
    }
  }
  console.log("Done.");
}

main();
