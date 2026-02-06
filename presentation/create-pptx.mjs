import pptxgen from 'pptxgenjs';
import path from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

const require = createRequire(import.meta.url);
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// html2pptx 라이브러리
const html2pptx = require('C:/Users/USER/.claude/plugins/cache/anthropic-agent-skills/example-skills/00756142ab04/skills/pptx/scripts/html2pptx.js');

async function createPresentation() {
    const pptx = new pptxgen();

    // 프레젠테이션 메타데이터
    pptx.layout = 'LAYOUT_16x9';
    pptx.author = 'rKYC Team';
    pptx.title = 'rKYC Multi-Agent Architecture';
    pptx.subject = 'Hackathon 2026 Presentation';

    const slidesDir = path.join(__dirname, 'slides');

    // 슬라이드 파일 목록
    const slideFiles = [
        'slide1-title.html',
        'slide2-problem.html',
        'slide3-solution.html',
        'slide4-architecture.html',
        'slide5-fallback.html',
        'slide6-agents.html',
        'slide7-techstack.html',
        'slide8-pipeline.html',
        'slide9-demo.html',
        'slide10-closing.html'
    ];

    // 각 슬라이드 변환
    for (const slideFile of slideFiles) {
        const htmlPath = path.join(slidesDir, slideFile);
        console.log(`Processing: ${slideFile}`);

        try {
            await html2pptx(htmlPath, pptx, {
                tmpDir: path.join(__dirname, 'workspace')
            });
        } catch (error) {
            console.error(`Error processing ${slideFile}:`, error.message);
            throw error;
        }
    }

    // 저장
    const outputPath = path.join(__dirname, 'rKYC-Multi-Agent-Architecture.pptx');
    await pptx.writeFile({ fileName: outputPath });
    console.log(`\nPresentation created successfully: ${outputPath}`);
}

createPresentation().catch(err => {
    console.error('Failed to create presentation:', err);
    process.exit(1);
});
