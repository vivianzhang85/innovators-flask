// Connect to Flask backend for saving outfits
class FlaskConnector {
    constructor(baseUrl = 'http://localhost:5001') {
        this.baseUrl = baseUrl;
    }
    
    async saveOutfitToBackend(outfit) {
        try {
            const response = await fetch(`${this.baseUrl}/api/data`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    type: 'met_outfit',
                    data: outfit,
                    scraped_at: new Date().toISOString()
                })
            });
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const result = await response.json();
            console.log('Saved to backend:', result);
            return result;
            
        } catch (error) {
            console.error('Error saving to backend:', error);
            return null;
        }
    }
    
    async getSavedOutfits() {
        try {
            const response = await fetch(`${this.baseUrl}/api/data`);
            
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            
            const data = await response.json();
            
            // Filter for MET outfits
            const metOutfits = Array.isArray(data) ? 
                data.filter(item => item.type === 'met_outfit') : 
                [];
            
            return metOutfits.map(item => item.data);
            
        } catch (error) {
            console.error('Error getting saved outfits:', error);
            return [];
        }
    }
}

export default FlaskConnector;