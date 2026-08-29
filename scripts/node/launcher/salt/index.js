const fs = require("fs");
const path = require("path");
const axios = require("axios");
const fse = require("fs-extra");
const yaml = require("js-yaml");
const asar = require('@electron/asar');  
const { path7za } = require("7zip-bin");
const { execFile } = require("child_process");

try {
    fs.chmodSync(path7za, 0o755);
} catch (err) {
    console.warn("The execution permission for 7za cannot be set, but the operation will continue to be attempted...");
}

const SERVERS = {
    CN: {
        TAG: "StellaSora_CN",
        API_URL: "https://launcher-api.yostar.net",
        PKG_URL: "https://game-launcher-ss-cn.yostar.net",
        PKG_ROUTE: "/pubplat/game-launcher-cn/install_pkg/launcher",
    },
    EN: {
        TAG: "StellaSora_EN",
        API_URL: "https://api-launcher-en.yo-star.com",
        PKG_URL: "https://launcher-pkg-ss-en.yo-star.com",
        PKG_ROUTE: "/install_pkg/game_launcher",
    },
    JP: {
        TAG: "StellaSora_JP",
        API_URL: "https://api-launcher-jp.yo-star.com",
        PKG_URL: "https://launcher-pkg-ss-jp.yo-star.com",
        PKG_ROUTE: "/install_pkg/game_launcher",
    },
    KR: {
        TAG: "StellaSora_KR",
        API_URL: "https://api-launcher-kr.yo-star.com",
        PKG_URL: "https://launcher-pkg-ss-kr.yo-star.com",
        PKG_ROUTE: "/install_pkg/game_launcher",
    },
    TW: {
        TAG: "StellaSora_TW",
        API_URL: "https://api-launcher-tw.stargazer-games.com",
        PKG_URL: "https://launcher-pkg-ss-hk.stargazer-games.com",
        PKG_ROUTE: "/install_pkg/game_launcher",
    },
};

function buildUrl(base, ...segments) {
    let url = new URL(base);
    for (const seg of segments) {
        if (!seg) continue;
        if (!url.pathname.endsWith("/")) url.pathname += "/";
        const cleanSeg = seg.replace(/^\/+/, "");
        url = new URL(cleanSeg, url);
    }
    return url.href;
}

const createRegionAxiosClient = (region) => {
    const config = SERVERS[region];
    if (!config) throw new Error(`Unknown region: ${region}`);

    const client = axios.create({
        timeout: 3e4,
        baseURL: config.API_URL,
        withCredentials: true,
        headers: { "Content-Type": "application/json;charset=UTF-8" },
    });

    client.interceptors.request.use(async (cfg) => {
        if (cfg._isDownload) {
            cfg.headers = new axios.AxiosHeaders({ "Cache-Control": "no-cache" });
            cfg.baseURL = "";
            cfg.withCredentials = false;
        }
        return cfg;
    });

    client.interceptors.response.use(
        (res) => res.data,
        (err) => Promise.reject(err),
    );

    return client;
};

const axiosCache = {};
const getRegionAxiosClient = (region) => {
    if (!axiosCache[region]) axiosCache[region] = createRegionAxiosClient(region);
    return axiosCache[region];
};

const downloader = async (targetUrl, destPath) => {
    await fse.ensureDir(path.dirname(destPath));
    const tmpPath = `${destPath}.tmp`;
    try {
        const response = await axios.get(targetUrl, { responseType: "stream" });
        const writer = fs.createWriteStream(tmpPath);

        await new Promise((resolve, reject) => {
            response.data.pipe(writer);
            response.data.on("error", reject);
            writer.on("error", reject);
            writer.on("finish", resolve);
        });

        await fse.move(tmpPath, destPath, { overwrite: true });
        console.log(`✅ Download successful: ${destPath}`);
    } catch (err) {
        console.error(`❌ Download failed: ${err.message}`);
        await fse.remove(tmpPath).catch(() => {});
        throw err;
    }
};


const run7z = async (args) => {
    return new Promise((resolve, reject) => {
        execFile(path7za, args, (error, stdout, stderr) => {
            if (error) reject(new Error(`7z failed: ${stderr || error.message}`));
            else resolve(stdout);
        });
    });
};

const extractWith7z = (exePath, outputDir) =>
    run7z(["x", "-t#", exePath, `-o${outputDir}`, "-y"]);

const findAndExtract7z = async (sourceDir, targetDir) => {
    const files = await fse.readdir(sourceDir);
    const sevenZFiles = files.filter((f) => f.endsWith(".7z") && /^\d+\.7z$/.test(f));
    if (sevenZFiles.length === 0) throw new Error("No numbered .7z files found.");

    const stats = await Promise.all(
        sevenZFiles.map(async (f) => ({
            name: f,
            size: (await fse.stat(path.join(sourceDir, f))).size,
        })),
    );
    const target = stats.sort((a, b) => b.size - a.size)[0];

    console.log(`📦 Target 7z: ${target.name} (${(target.size / 1024 / 1024).toFixed(1)} MB)`);
    return run7z(["x", "-t7z", path.join(sourceDir, target.name), `-o${targetDir}`, "-aoa", "-y"]);
};

const cleanTemp = async (sourceDir) => {
    const entries = await fse.readdir(sourceDir, { withFileTypes: true });
    for (const entry of entries) {
        if (entry.isFile() && !entry.name.endsWith(".7z")) {
            await fse.remove(path.join(sourceDir, entry.name));
        }
    }
};

const extractSaltFromFile = (filePath) => {
    const content = fse.readFileSync(filePath, "utf8");
    const match = content.match(/salt\s*:\s*[""]([^""]+)["']/);
    if (!match) throw new Error(`Salt not found in: ${filePath}`);
    return match[1];
};


(async () => {
    const ROOT_OUTPUT    = "./output";
    const DATA_STORAGE   = "data_storage";
    const PKG_LATEST_YML = "latest.yml";
    const SALT_OUTPUT    = "launcher_salt.json";
    
    const saltData = {};

    for (const [region, { TAG, PKG_URL, PKG_ROUTE }] of Object.entries(SERVERS)) {
        console.log(`\n🚀 Processing region: ${region}`);

        const pkgBaseUrl = buildUrl(PKG_URL, PKG_ROUTE, TAG);
        const retrieveUrl = buildUrl(pkgBaseUrl, PKG_LATEST_YML);
        
        console.log(`⬇️ Fetching: ${retrieveUrl}`);
        const ymlContent = await getRegionAxiosClient(region).get(retrieveUrl, { _isDownload: true });
        const latestConfig = yaml.load(ymlContent, { schema: yaml.FAILSAFE_SCHEMA });
        const regionOutputDir = path.join(ROOT_OUTPUT, region);
        await fse.outputFile(path.join(regionOutputDir, PKG_LATEST_YML), ymlContent);

        const targetLauncherPath = latestConfig?.path;
        const launcherVersion = latestConfig?.version;
        if (!targetLauncherPath) throw new Error(`latest.yml missing "path" field for ${region}`);

        const launcherUrl = buildUrl(pkgBaseUrl, targetLauncherPath);
        const storageDir = path.join(DATA_STORAGE, region);
        const launcherDest = path.join(storageDir, path.basename(targetLauncherPath));

        console.log(`⬇️ Downloading launcher: ${launcherUrl}`);
        await downloader(launcherUrl, launcherDest);

        const tempDir = path.join(storageDir, "temp");
        const finalDir = path.join(storageDir, "final");
        await fse.ensureDir(tempDir);
        await fse.ensureDir(finalDir);

        console.log("📂 Extracting installer...");
        await extractWith7z(launcherDest, tempDir);

        console.log("📂 Extracting game assets...");
        await findAndExtract7z(tempDir, finalDir);

        console.log("🧹 Cleaning temp files...");
        await cleanTemp(tempDir);

        const asarPath = path.join(finalDir, "resources", "app.asar");
        const asarOutDir = path.join(finalDir, "source");

        if (!(await fse.pathExists(asarPath))) {
            throw new Error(`app.asar not found at: ${asarPath}`);
        }

        console.log("📦 Extracting app.asar...");
        asar.extractAll(asarPath, asarOutDir);

        const saltFilePath = path.join(asarOutDir, "out", "main", "index.js");
        const salt = extractSaltFromFile(saltFilePath);

        console.log(`🔑 Salt (${region}): ${salt}`);
        saltData[region] = {salt: salt, ver: launcherVersion};
    }

    console.log("\n✅ All regions processed successfully.");
    await fse.outputFile(path.join(ROOT_OUTPUT, SALT_OUTPUT), 
        JSON.stringify(saltData, null, 4), {encoding: "utf-8"}
    );

})().catch((err) => {
    console.error("\n💥 Fatal error:", err);
    process.exit(1);
});
