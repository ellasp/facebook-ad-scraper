document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const urlPatternsContainer = document.getElementById('urlPatterns');
    const addUrlPatternBtn = document.getElementById('addUrlPattern');
    const loadingIndicator = document.getElementById('loading');
    const resultsSection = document.getElementById('results');
    const resultsBody = document.getElementById('resultsBody');
    const errorAlert = document.getElementById('errorAlert');
    const downloadBtn = document.getElementById('downloadBtn');
    
    let currentMatches = [];
    
    // Add URL pattern input
    addUrlPatternBtn.addEventListener('click', function() {
        const newGroup = document.createElement('div');
        newGroup.className = 'input-group mb-2 url-pattern-group';
        newGroup.innerHTML = `
            <input type="text" class="form-control url-pattern" placeholder="e.g., https://example.com" required>
            <button type="button" class="btn btn-outline-danger remove-url">
                <i class="fas fa-trash"></i>
            </button>
        `;
        urlPatternsContainer.appendChild(newGroup);
        
        // Show remove button for all groups if there's more than one
        updateRemoveButtons();
    });
    
    // Remove URL pattern input
    urlPatternsContainer.addEventListener('click', function(e) {
        if (e.target.closest('.remove-url')) {
            e.target.closest('.url-pattern-group').remove();
            updateRemoveButtons();
        }
    });
    
    // Update remove buttons visibility
    function updateRemoveButtons() {
        const groups = urlPatternsContainer.querySelectorAll('.url-pattern-group');
        groups.forEach(group => {
            const removeBtn = group.querySelector('.remove-url');
            removeBtn.style.display = groups.length > 1 ? 'block' : 'none';
        });
    }
    
    // Handle form submission
    searchForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        // Get all URL patterns
        const urlPatterns = Array.from(document.querySelectorAll('.url-pattern')).map(input => input.value.trim());
        const searchTerm = document.getElementById('searchTerm').value.trim();
        
        if (!searchTerm) {
            showError('Please enter a search term');
            return;
        }
        
        // Show loading indicator
        loadingIndicator.style.display = 'block';
        resultsSection.style.display = 'none';
        errorAlert.style.display = 'none';
        
        try {
            const response = await fetch('/search', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    search_term: searchTerm,
                    url_patterns: urlPatterns
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                showError(data.error);
                return;
            }
            
            currentMatches = data.matches;
            displayResults(data);
            
        } catch (error) {
            showError('An error occurred while searching. Please try again.');
            console.error('Search error:', error);
        } finally {
            loadingIndicator.style.display = 'none';
        }
    });
    
    // Display results
    function displayResults(data) {
        resultsSection.style.display = 'block';
        
        // Update regular results
        if (!data.matches || data.matches.length === 0) {
            resultsBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center">No matching ads found</td>
                </tr>
            `;
            downloadBtn.disabled = true;
            return;
        }
        
        // Display regular results
        const resultsHtml = data.matches.map(match => `
            <tr>
                <td>${match.image_url ? `<a href="${match.image_url}" target="_blank"><img src="${match.image_url}" alt="Ad Image" style="max-width: 100px; max-height: 100px;"></a>` : 'N/A'}</td>
                <td>${match.ad_text || 'N/A'}</td>
                <td><a href="${match.library_link}" target="_blank">${match.library_id || 'N/A'}</a></td>
                <td><a href="${match.ad_page_url}" target="_blank">${match.ad_page_url || 'N/A'}</a></td>
                <td><a href="${match.original_url}" target="_blank">${match.original_url || 'N/A'}</a></td>
                <td><a href="${match.final_url}" target="_blank">${match.final_url || 'N/A'}</a></td>
            </tr>
        `).join('');
        
        resultsBody.innerHTML = resultsHtml;

        // Display flagged results
        const flaggedResultsBody = document.getElementById('flaggedResultsBody');
        if (data.flagged_ads && data.flagged_ads.length > 0) {
            const flaggedHtml = data.flagged_ads.map(match => `
                <tr>
                    <td>${match.image_url ? `<a href="${match.image_url}" target="_blank"><img src="${match.image_url}" alt="Ad Image" style="max-width: 100px; max-height: 100px;"></a>` : 'N/A'}</td>
                    <td>${match.ad_text || 'N/A'}</td>
                    <td><a href="${match.library_link}" target="_blank">${match.library_id || 'N/A'}</a></td>
                    <td><a href="${match.ad_page_url}" target="_blank">${match.ad_page_url || 'N/A'}</a></td>
                    <td><a href="${match.original_url}" target="_blank">${match.original_url || 'N/A'}</a></td>
                    <td><a href="${match.final_url}" target="_blank">${match.final_url || 'N/A'}</a></td>
                    <td>${match.matched_words ? match.matched_words.join(', ') : 'N/A'}</td>
                </tr>
            `).join('');
            flaggedResultsBody.innerHTML = flaggedHtml;
        } else {
            flaggedResultsBody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center">No flagged ads found</td>
                </tr>
            `;
        }
        
        downloadBtn.disabled = false;
    }
    
    // Show error message
    function showError(message) {
        errorAlert.textContent = message;
        errorAlert.style.display = 'block';
    }
    
    // Handle download button click
    let selectedFormat = 'json'; // Default format
    
    // Handle format selection
    document.querySelectorAll('.dropdown-item').forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            selectedFormat = this.dataset.format;
            downloadResults();
        });
    });
    
    // Handle main download button click
    downloadBtn.addEventListener('click', function() {
        downloadResults();
    });
    
    async function downloadResults() {
        if (currentMatches.length === 0) return;
        
        try {
            const response = await fetch('/download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    matches: currentMatches,
                    format: selectedFormat
                })
            });
            
            if (!response.ok) {
                throw new Error('Download failed');
            }
            
            // Get the filename from the response headers if available
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = 'facebook_ad_matches.' + selectedFormat;
            if (contentDisposition) {
                const matches = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (matches && matches[1]) {
                    filename = matches[1].replace(/['"]/g, '');
                }
            }
            
            // Create a blob from the response
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
        } catch (error) {
            console.error('Download error:', error);
            showError('Failed to download results. Please try again.');
        }
    }
    
    // Cleanup when window is closed
    window.addEventListener('beforeunload', async function() {
        try {
            await fetch('/cleanup', {
                method: 'POST'
            });
        } catch (error) {
            console.error('Cleanup error:', error);
        }
    });
}); 