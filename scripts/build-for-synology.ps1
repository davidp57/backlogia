# Build and export Docker image for Synology NAS deployment
# This script is OPTIONAL - the recommended method is to use GitHub Actions
#
# Requirements:
#   - Docker Desktop installed and running
#   - PowerShell 5.1 or later
#
# Usage:
#   .\scripts\build-for-synology.ps1

param(
    [string]$OutputPath = ".",
    [switch]$SkipCompression
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Backlogia - Build for Synology NAS" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "[1/5] Checking Docker..." -ForegroundColor Yellow
try {
    docker version | Out-Null
    Write-Host "[OK] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker is not running or not installed" -ForegroundColor Red
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Build the Docker image
Write-Host ""
Write-Host "[2/5] Building Docker image..." -ForegroundColor Yellow
docker compose build
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker build failed" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Image built successfully" -ForegroundColor Green

# Export image to TAR
Write-Host ""
Write-Host "[3/5] Exporting image to TAR..." -ForegroundColor Yellow
$tarPath = Join-Path $OutputPath "backlogia.tar"
docker save backlogia-backlogia:latest -o $tarPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to export image" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Image exported to: $tarPath" -ForegroundColor Green

# Compress TAR file (optional)
if (-not $SkipCompression) {
    Write-Host ""
    Write-Host "[4/5] Compressing TAR file..." -ForegroundColor Yellow

    # Check if gzip is available
    $gzipAvailable = Get-Command gzip -ErrorAction SilentlyContinue

    if ($gzipAvailable) {
        gzip $tarPath
        $gzPath = "$tarPath.gz"
        Write-Host "[OK] Image compressed to: $gzPath" -ForegroundColor Green
        $finalFile = $gzPath
    } else {
        Write-Host "[WARN] gzip not found - skipping compression" -ForegroundColor Yellow
        Write-Host "  You can manually compress the file or transfer it as-is" -ForegroundColor Gray
        $finalFile = $tarPath
    }
} else {
    Write-Host ""
    Write-Host "[4/5] Skipping compression (--SkipCompression flag)" -ForegroundColor Yellow
    $finalFile = $tarPath
}

# Get file size
Write-Host ""
Write-Host "[5/5] Checking file size..." -ForegroundColor Yellow
$fileSize = (Get-Item $finalFile).Length / 1MB
Write-Host "[OK] Final file size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Green

# Display next steps
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Build Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Transfer the image to your Synology NAS:" -ForegroundColor White
Write-Host "   - Via File Station: Upload '$finalFile' to /docker/images/" -ForegroundColor Gray
Write-Host "   - Via SCP: scp '$finalFile' admin@[NAS-IP]:/volume1/docker/images/" -ForegroundColor Gray
Write-Host ""
Write-Host "2. On the NAS, import the image:" -ForegroundColor White
if ($finalFile -like "*.gz") {
    Write-Host "   gunzip /volume1/docker/images/backlogia.tar.gz" -ForegroundColor Gray
}
Write-Host "   docker load -i /volume1/docker/images/backlogia.tar" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Deploy using Container Manager UI or docker-compose:" -ForegroundColor White
Write-Host "   - UI: Container Manager -> Container -> Create -> Select 'backlogia:latest'" -ForegroundColor Gray
Write-Host "   - CLI: docker compose -f docker-compose.synology.yml up -d" -ForegroundColor Gray
Write-Host ""
Write-Host "4. Access Backlogia at http://[NAS-IP]:5050" -ForegroundColor White
Write-Host ""
Write-Host "For detailed instructions, see: docs/synology-deployment.md" -ForegroundColor Cyan
Write-Host ""
