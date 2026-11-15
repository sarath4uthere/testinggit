// Dependency-free "build": copies src/ to dist/ and stamps the version into the files.
const fs = require("fs");
const path = require("path");

const version = process.env.VERSION || "dev";
const srcDir = path.join(__dirname, "src");
const outDir = path.join(__dirname, "dist");

fs.rmSync(outDir, { recursive: true, force: true });
fs.mkdirSync(outDir, { recursive: true });

for (const file of fs.readdirSync(srcDir)) {
  const text = fs.readFileSync(path.join(srcDir, file), "utf8");
  fs.writeFileSync(path.join(outDir, file), text.replaceAll("__APP_VERSION__", version));
}
fs.writeFileSync(path.join(outDir, "version.txt"), version + "\n");
console.log(`built web assets, version ${version}`);
