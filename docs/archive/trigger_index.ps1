$docs = Invoke-RestMethod -Uri 'http://localhost:8000/api/v1/acquisition/queue'
$indexedDocs = $docs | Where-Object { $_.status -eq 'INDEXED' -or $_.status -eq 'METADATA_REVIEW' -or $_.status -eq 'FULL_REVIEW' }

foreach ($d in $indexedDocs) {
    if ($d.local_file_path) {
        Write-Host "Triggering index for: $($d.title) ($($d._id))"
        try {
            $response = Invoke-RestMethod -Method Put -Uri "http://localhost:8000/api/v1/acquisition/queue/$($d._id)/approve-index"
            Write-Host "Success: $($response.job_id)"
        } catch {
            Write-Host "Error triggering index for $($d._id): $_"
        }
    }
}
