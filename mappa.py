# %%
import geopandas as gpd
import folium
from folium import GeoJson, Element
import json
import webbrowser
import os
import unicodedata
import re


# %% Helper function to normalize strings (remove diacritics and parentheses)
def normalize_string(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")  # Remove diacritics
    return re.sub(r"[()]", "", s).strip().lower()  # Remove parentheses


# %% Function to assign colors to provinces
def get_province_color(province_code):
    color_map = {
        81: "#FFB400",  # Warm Gold
        84: "#FF6F61",  # Soft Coral Red
        85: "#9370DB",  # Medium Purple
        86: "#E9967A",  # Muted Salmon
        88: "#708090",  # Slate Grey
        89: "#D9534F",  # Rich Tomato Red
        280: "#00A86B",  # Deep Jade Green
        282: "#4682B4",  # Soft Steel Blue
        283: "#40E0D0",  # Turquoise
        287: "#9932CC",  # Dark Orchid Purple
    }
    return color_map.get(province_code, "#2F4F4F")  # Default: Dark Slate Grey for contrast


# %% Load geographical data
map_data = gpd.read_file("../finaiti/basidati.gpkg", layer="cumuna")
provinces = gpd.read_file("../finaiti/basidati.gpkg", layer="pruvinci")

# %% Map province codes to names
province_mapping = {row["COD_UTS"]: row["SCN"] for _, row in provinces.iterrows()}

# %% Create the map
min_lat, max_lat = 34.7, 39.7
min_lon, max_lon = 12.0, 17.5
m = folium.Map(
    location=(37.2, 15.0),
    zoom_start=8,
    max_bounds=True,
    min_lat=min_lat,
    max_lat=max_lat,
    min_lon=min_lon,
    max_lon=max_lon,
    tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}",
    attr="Tiles &copy; Esri &mdash; Source: Esri",
    # tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    # attr="Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
    # tiles='https://{s}.basemaps.cartocdn.com/rastertiles/voyager_nolabels/{z}/{x}/{y}{r}.png',
    # attr='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
)

# Add CSS link
m.get_root().html.add_child(
    folium.Element(
"""
<link rel="stylesheet" type="text/css" href="css/map-styles.css">
"""
    )
)

m.get_root().html.add_child(
    folium.Element(
f"""
<script>
    document.addEventListener("DOMContentLoaded", function() {{
        window.map = {m.get_name()};
    }});
</script>
"""
    )
)

# %% Inject global JavaScript functions
global_js = """
<script>
    function highlightFeature(id) {
        for (var key in window.layer_map) {
            if (window.layer_map.hasOwnProperty(key)) {
                var lyr = window.layer_map[key];
                var origColor = lyr.options.originalColor || lyr.options.color;
                lyr.setStyle({ fillOpacity: 0.3, color: origColor });
                lyr.selected = false;
            }
        }
        var layer = window.layer_map[id];
        if (layer) {
            layer.setStyle({ fillOpacity: 0.8, color: '#1E90FF' });
            layer.selected = true;
        }
    }

    function toggleSidebarInfo(id) {
        var sidebar = document.getElementById("sidebar");
        var infoBoxes = document.querySelectorAll('[id^="info_layer_"]');
        infoBoxes.forEach(function(div) {
            div.style.display = 'none';
        });
        var infoDiv = document.getElementById("info_" + id);
        if (!infoDiv) return;
        if (infoDiv.style.display === "none" || infoDiv.style.display === "") {
            infoDiv.innerHTML = window.layer_info[id] || "No info available.";
            infoDiv.style.display = "block";
            // Calculate search container height dynamically
            var searchContainer = document.querySelector(".search-container");
            var searchHeight = searchContainer ? searchContainer.offsetHeight : 60;
            var offset = 75 + searchHeight; // Account for search bar height
            sidebar.scrollTo({ top: infoDiv.offsetTop - offset, behavior: "smooth" });
        } else {
            infoDiv.style.display = "none";
        }
    }

    function expandSectionForLayer(layer_id) {
        var infoElem = document.getElementById("info_" + layer_id);
        if(infoElem) {
            var placesList = infoElem.parentElement.parentElement;
            if(placesList && placesList.classList.contains("places-list")) {
                placesList.style.transition = "max-height 0.4s ease-out";
                placesList.style.maxHeight = placesList.scrollHeight + "px";
                placesList.classList.add("expanded");
                setTimeout(function(){
                    var sidebar = document.getElementById("sidebar");
                    // Calculate search container height dynamically
                    var searchContainer = document.querySelector(".search-container");
                    var searchHeight = searchContainer ? searchContainer.offsetHeight : 60;
                    var offset = 75 + searchHeight; // Account for search bar height
                    sidebar.scrollTo({ top: infoElem.offsetTop - offset, behavior: "smooth" });
                }, 400);
            }
        }
    }
    
    function showLabelWithLine(id, name, lat, lon, geometry = null) {
        // Store current label data
        window.currentLabelData = {id: id, name: name, lat: lat, lon: lon};
        
        // Use new ultra-responsive Arrow UI system
        if (window.arrowUI) {
            window.arrowUI.showArrow(id, name, lat, lon, geometry);
        }
    }

    function showLabelFromSidebar(layer_id) {
        var coords = window.layer_coordinates[layer_id];
        if (coords) {
            // Prova a ottenere la geometria dal layer mappato
            var layer = window.layer_map[layer_id];
            var geometry = null;
            if (layer && layer.feature && layer.feature.geometry) {
                geometry = layer.feature.geometry;
            }
            showLabelWithLine(layer_id, coords.name, coords.lat, coords.lon, geometry);
        }
    }

    window.layer_map = {};
    window.layer_info = {};
    
    // Global settings for calibration  
    window.labelSettings = {
        distanceMultiplier: 1.0,
        fontSizeMultiplier: 1.0
    };
    
    // Initialize Arrow UI system when map is ready
    document.addEventListener("DOMContentLoaded", function() {
        // Wait for map to be fully loaded
        setTimeout(function() {
            if (window.ArrowUI && window.map) {
                window.arrowUI = new window.ArrowUI(window.map);
                console.log("Ultra-responsive Arrow UI system initialized!");
            }
        }, 500);
    });
    
    // Set dynamic province border colors
    document.addEventListener("DOMContentLoaded", function() {
        var provinceBlocks = document.querySelectorAll(".province-block");
        provinceBlocks.forEach(function(block) {
            var color = block.getAttribute("data-province-color");
            if (color) {
                block.style.borderLeftColor = color;
            }
        });
    });
    
    console.log("Global JS functions and objects defined.");
</script>
"""
m.get_root().html.add_child(Element(global_js))

# %% Prepare HTML for the sidebar
layer_info_dict = {}
layer_coordinates = {}
locations_html = "<ul id='location-list'>"

# Group the cumuna data by the 'COD_UTS' field.
grouped = map_data.groupby("COD_UTS")

# Group cumuna data by province and sort alphabetically
sorted_province_codes = sorted(
    grouped.groups.keys(),
    key=lambda pc: normalize_string(province_mapping.get(pc, f"Province {pc}")),
)

for province_code in sorted_province_codes:
    province_name = province_mapping.get(province_code, f"Province {province_code}")
    province_color = get_province_color(province_code)

    group_df = grouped.get_group(province_code)
    group_sorted = group_df.sort_values(
        "SCN", key=lambda s: s.fillna("").apply(normalize_string)
    )

    place_items_html = []
    scn_to_layerid = {}

    # Iterate over places
    for idx, row in group_sorted.iterrows():
        layer_id = f"layer_{idx}"
        local_name = row["LUCALI"] if row["LUCALI"] != row["SCN"] else None

        info_str = f"""
            <div class="info-box">
                <span class="info-italian">{row['ITA']}</span>
        """
        if local_name:
            info_str += f"""
                <span class="info-location">
                    &#128205; {local_name}
                </span>
            """
        if row.get("ABBITANTI"):
            info_str += f"""
                <span class="info-demonym">
                    &#129489; {row['ABBITANTI']}
                </span>
            """
        else:
            info_str += """
                <span class="info-demonym">
                    &#129489; ?
                </span>
            """
        if row.get("NOTI"):
            info_str += f"""
                <span class="info-noti">
                    {row['NOTI']}
                </span>
            """
        info_str += "</div>"

        layer_info_dict[layer_id] = info_str

        # Store coordinates for sidebar clicks
        centroid = row.geometry.centroid
        layer_coordinates[layer_id] = {
            "lat": centroid.y,
            "lon": centroid.x,
            "name": row["SCN"] if row["SCN"] else "?",
        }

        # Sidebar list item
        place_items_html.append(
            f"""
        <li class="place-item"
                data-sicilian-name="{row['SCN'] if row['SCN'] else ''}"
                data-italian-name="{row['ITA'] if row['ITA'] else ''}"
                data-local-pron="{row['LUCALI'] if row['LUCALI'] else ''}"
            >
            <a href="#" onclick="toggleSidebarInfo('{layer_id}'); highlightFeature('{layer_id}'); expandSectionForLayer('{layer_id}'); showLabelFromSidebar('{layer_id}'); return false;">
                {row["SCN"] if row["SCN"] else "?"}
            </a>
            <div id="info_{layer_id}" style="display:none;"></div>
        </li>
        """
        )

        if row["SCN"]:
            scn_to_layerid[row["SCN"]] = layer_id

        # Create a GeoJson layer for each place
        lyr = GeoJson(
            row["geometry"],
            name=row["ITA"],
            style_function=lambda _, color=province_color: {
                "color": color,
                "weight": 1.5,
                # "fillColor": color,
                "fillOpacity": 0.3,
            },
        ).add_to(m)
        lyr.options["originalColor"] = province_color

        # Attach events to the layer
        layer_js_name = lyr.get_name()
        js_assign = f"""
        <script>
            document.addEventListener("DOMContentLoaded", function() {{
                window.layer_map["{layer_id}"] = {layer_js_name};
                {layer_js_name}.on("click", function(e) {{
                    toggleSidebarInfo("{layer_id}");
                    highlightFeature("{layer_id}");
                    expandSectionForLayer("{layer_id}");
                    
                    var center = e.target.getBounds().getCenter();
                    // Passa la geometria del layer per calcolo punto interno
                    if (window.arrowUI && e.target.feature) {{
                        window.arrowUI.showArrow("{layer_id}", "{row['SCN']}", center.lat, center.lng, e.target.feature.geometry);
                    }} else {{
                        showLabelWithLine("{layer_id}", "{row['SCN']}", center.lat, center.lng);
                    }}
                }});
                {layer_js_name}.on("mouseover", function(e) {{
                    if (!{layer_js_name}.selected) {{
                        {layer_js_name}.setStyle({{ fillOpacity: 0.6, color: '#1E90FF' }});
                    }}
                }});
                {layer_js_name}.on("mouseout", function(e) {{
                    if (!{layer_js_name}.selected) {{
                        var origColor = {layer_js_name}.options.originalColor || {layer_js_name}.options.color;
                        {layer_js_name}.setStyle({{ fillOpacity: 0.3, color: origColor }});
                    }}
                }});
            }});
        </script>
        """
        m.get_root().html.add_child(Element(js_assign))

    # Province header with expandable list
    locations_html += f"""
    <li class="province-block" style="border-left: 6px solid {province_color};">
        <span class="province-header">{province_name}</span>
        <ul class="places-list" style="max-height: 0; overflow: hidden; transition: max-height 0.4s ease-out;">
            {''.join(place_items_html)}
        </ul>
    </li>
    """

locations_html += "</ul>"

# Inject layer info and coordinates into global JS
js_layer_info = f"<script>window.layer_info = {json.dumps(layer_info_dict)};</script>"
js_layer_coordinates = (
    f"<script>window.layer_coordinates = {json.dumps(layer_coordinates)};</script>"
)
m.get_root().html.add_child(Element(js_layer_info))
m.get_root().html.add_child(Element(js_layer_coordinates))

# %% Add collapse toggle functionality for province headers with smooth transitions
collapse_js = """
<script>
document.addEventListener("DOMContentLoaded", function() {
    var headers = document.querySelectorAll(".province-header");
    headers.forEach(function(header) {
        header.addEventListener("click", function() {
            var placesList = header.nextElementSibling;
            var provinceBlock = header.parentElement;
            if (placesList) {
                if (placesList.classList.contains("expanded")) {
                    placesList.style.transition = "max-height 0.3s ease-in";
                    placesList.style.maxHeight = "0";
                    placesList.classList.remove("expanded");
                    provinceBlock.classList.remove("expanded");
                } else {
                    placesList.style.transition = "max-height 0.4s ease-out";
                    placesList.style.maxHeight = placesList.scrollHeight + "px";
                    placesList.classList.add("expanded");
                    provinceBlock.classList.add("expanded");
                }
            }
        });
    });
});
</script>
"""
m.get_root().html.add_child(Element(collapse_js))

# %% Include Turf.js for geometry calculations
turf_script = """
<script src="https://unpkg.com/@turf/turf@6/turf.min.js"></script>
"""
m.get_root().html.add_child(Element(turf_script))

# %% Include Arrow UI System
arrow_ui_script = """
<script>
console.log('Defining ArrowUI class inline...');

class ArrowUI {
    constructor(map) {
        this.map = map;
        this.currentArrow = null;
        this.currentLabel = null;
        this.currentGeometry = null;
        this.currentStartPoint = null; // Salvo il punto di partenza fisso
        this.currentAngle = null; // Salvo l'angolo fisso
        this.settings = {
            distanceMultiplier: 1.0,
            fontSizeMultiplier: 1.0
        };
        
        // Listen for zoom changes - SOLO scalatura, NO cambio angolo
        this.map.on('zoomend', () => {
            if (this.currentStartPoint && this.currentAngle !== null) {
                this.updateArrowForZoom();
            }
        });
        
        console.log('Simplified ArrowUI initialized');
    }

    updateSettings(newSettings) {
        Object.assign(this.settings, newSettings);
        if (this.currentStartPoint && this.currentAngle !== null) {
            this.updateArrowForZoom();
        }
    }

    // Trova il punto interno più vicino al centroide
    findInteriorPoint(geometry) {
        try {
            // Calcola il centroide come riferimento
            const centroid = turf.centroid(geometry);
            
            // Se il centroide è già dentro, usalo
            if (turf.booleanPointInPolygon(centroid, geometry)) {
                return [centroid.geometry.coordinates[1], centroid.geometry.coordinates[0]];
            }
            
            // ALTRIMENTI: usa SEMPRE il pole of inaccessibility
            // Questo è il punto più interno possibile nell'area
            const polylabel = turf.polylabel(geometry);
            return [polylabel.geometry.coordinates[1], polylabel.geometry.coordinates[0]];
            
        } catch (error) {
            console.warn('Error finding interior point, using fallback:', error);
            // Fallback: usa il bbox center e controlla se è interno
            const bbox = turf.bbox(geometry);
            const centerLat = (bbox[1] + bbox[3]) / 2;
            const centerLon = (bbox[0] + bbox[2]) / 2;
            const centerPoint = turf.point([centerLon, centerLat]);
            
            if (turf.booleanPointInPolygon(centerPoint, geometry)) {
                return [centerLat, centerLon];
            }
            
            // Se anche questo fallisce, usa polylabel
            try {
                const polylabel = turf.polylabel(geometry);
                return [polylabel.geometry.coordinates[1], polylabel.geometry.coordinates[0]];
            } catch (e) {
                // Ultimo fallback: centroide grezzo
                const centroid = turf.centroid(geometry);
                return [centroid.geometry.coordinates[1], centroid.geometry.coordinates[0]];
            }
        }
    }

    showArrow(id, name, lat, lon, geometry = null) {
        this.currentArrowData = {id, name, lat, lon};
        this.currentGeometry = geometry;
        
        // Trova il punto interno una volta sola
        if (geometry) {
            this.currentStartPoint = this.findInteriorPoint(geometry);
        } else {
            this.currentStartPoint = [lat, lon];
        }
        
        // Calcola l'angolo una volta sola - direzione intelligente
        this.calculateFixedAngle();
        
        // Disegna la linea
        this.drawStraightLine(name);
    }

    calculateFixedAngle() {
        const [lat, lon] = this.currentStartPoint;
        
        // SEMPLICE: sposta TUTTE le scritte verso il mare (sud-ovest)
        // Angolo fisso verso il mare con piccola variazione casuale per naturalezza
        this.currentAngle = -Math.PI * 3/4 + (Math.random() - 0.5) * Math.PI/6; // -135° ± 15°
        // Questo punta verso sud-ovest (verso il mare) con variazione leggera
    }

    updateArrowForZoom() {
        if (this.currentStartPoint && this.currentAngle !== null) {
            this.drawStraightLine(this.currentArrowData.name);
        }
    }

    drawStraightLine(name) {
        this.clearArrow();
        
        const [startLat, startLon] = this.currentStartPoint;
        
        // INGRANDIMENTO DELLA MAPPA
        const currentZoom = this.map.getZoom();
        const baseZoom = 8;
        const zoomFactor = Math.pow(2, baseZoom - currentZoom);
        
        // LUNGHEZZA DELLA LINEA
        const baseLineLength = 0.425 * zoomFactor;
        const adjustedLength = baseLineLength * this.settings.distanceMultiplier;
        
        // PUNTO DEL TESTO
        const textGap = 0.1 * zoomFactor;
        const textLat = startLat + (adjustedLength + textGap) * Math.sin(this.currentAngle);
        const textLon = startLon + (adjustedLength + textGap) * Math.cos(this.currentAngle);
        
        // PUNTO FINALE DELLA LINEA
        const lineStopGap = 0.04 * zoomFactor; // Gap aumentato tra linea e testo
        const lineEndLat = startLat + (adjustedLength + lineStopGap) * Math.sin(this.currentAngle);
        const lineEndLon = startLon + (adjustedLength + lineStopGap) * Math.cos(this.currentAngle);
        
        // LA LINEA NON TOCCA LA SCRITTA
        this.currentArrow = L.polyline([
            [startLat, startLon],
            [lineEndLat, lineEndLon]  // Si ferma prima del testo
        ], {
            color: '#2C3E50',
            weight: 3,
            opacity: 0.9,
            lineCap: 'round'
        }).addTo(this.map);
        
        // TESTO con bordo semi trasparente
        const screenFontSize = 22;
        const adjustedFontSize = screenFontSize * this.settings.fontSizeMultiplier;
        
        // Calcola approssimativamente le dimensioni del testo per centrarlo
        const approxTextWidth = name.length * adjustedFontSize * 0.6; // Stima larghezza
        const approxTextHeight = adjustedFontSize; // Altezza del font
        
        const labelIcon = L.divIcon({
            className: 'simple-place-label',
            html: `<div class="place-label-text" style="font-size: ${adjustedFontSize}px;">${name}</div>`,
            iconAnchor: [approxTextWidth / 2, approxTextHeight / 2]  // CENTRO calcolato
        });
        
        this.currentLabel = L.marker([textLat, textLon], {
            icon: labelIcon,
            zIndexOffset: 1000
        }).addTo(this.map);
        
        // Hover effect semplice
        this.currentArrow.on('mouseover', () => {
            this.currentArrow.setStyle({
                opacity: 1,
                weight: 4,
                color: '#34495E'
            });
        });
        
        this.currentArrow.on('mouseout', () => {
            this.currentArrow.setStyle({
                opacity: 0.9,
                weight: 3,
                color: '#2C3E50'
            });
        });
    }

    clearArrow() {
        if (this.currentArrow) {
            this.map.removeLayer(this.currentArrow);
            this.currentArrow = null;
        }
        if (this.currentLabel) {
            this.map.removeLayer(this.currentLabel);
            this.currentLabel = null;
        }
    }
}
window.ArrowUI = ArrowUI;
</script>
"""
m.get_root().html.add_child(Element(arrow_ui_script))

# %% Sidebar HTML
sidebar_html = f"""
<div id="sidebar">
    <div class="search-container">
        <input type="text" id="search-box" placeholder="Riscedi u nomu sicilianu o chiḍḍu talianu...">
    </div>
    <ul id="location-list">
        {locations_html}
    </ul>
</div>
"""
m.get_root().html.add_child(Element(sidebar_html))

# %% Calibration Controls
calibration_html = """
<div id="calibration-panel">
    <div class="calibration-header">
        <span class="calibration-icon">⚙️</span>
        <span class="calibration-title">Mpustazzioni</span>
    </div>
    <div class="calibration-content">
        <div class="calibration-control">
            <label for="distance-slider">Lunghizza dâ linia</label>
            <input type="range" id="distance-slider" min="0.5" max="1.5" step="0.1" value="1.0">
            <span id="distance-value">1.0x</span>
        </div>
        <div class="calibration-control">
            <label for="font-slider">Grannizza dû testu</label>
            <input type="range" id="font-slider" min="0.5" max="1.5" step="0.1" value="1.0">
            <span id="font-value">1.0x</span>
        </div>
    </div>
</div>

<script>
    document.addEventListener("DOMContentLoaded", function() {
        var distanceSlider = document.getElementById("distance-slider");
        var fontSlider = document.getElementById("font-slider");
        var distanceValue = document.getElementById("distance-value");
        var fontValue = document.getElementById("font-value");
        
        // Update distance multiplier
        distanceSlider.addEventListener("input", function() {
        var value = parseFloat(this.value);
        window.labelSettings.distanceMultiplier = value;
        distanceValue.textContent = value.toFixed(1) + "x";
        
        // Update Arrow UI settings in real-time
        if (window.arrowUI) {
            window.arrowUI.updateSettings({distanceMultiplier: value});
        }
    });

    // Update font size multiplier
    fontSlider.addEventListener("input", function() {
        var value = parseFloat(this.value);
        window.labelSettings.fontSizeMultiplier = value;
        fontValue.textContent = value.toFixed(1) + "x";
        
        // Update Arrow UI settings in real-time
        if (window.arrowUI) {
            window.arrowUI.updateSettings({fontSizeMultiplier: value});
        }
    });

    // Search Box Logic
    const searchBox = document.getElementById('search-box');
    if (searchBox) {
        searchBox.addEventListener('input', function() {
            const searchTerm = this.value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
            const allPlaceItems = document.querySelectorAll('.place-item');

            allPlaceItems.forEach(item => {
                const sicilianName = (item.getAttribute('data-sicilian-name') || '').normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
                const italianName = (item.getAttribute('data-italian-name') || '').normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
                const localPron = (item.getAttribute('data-local-pron') || '').normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();

                if (sicilianName.includes(searchTerm) || italianName.includes(searchTerm) || localPron.includes(searchTerm)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });

            document.querySelectorAll('.province-block').forEach(province => {
                const visibleItems = province.querySelectorAll('.place-item:not([style*="display: none"])');
                if (visibleItems.length > 0) {
                    province.style.display = '';
                    // Optional: expand the province list if it was collapsed
                    const placesList = province.querySelector('.places-list');
                    if (placesList && !placesList.classList.contains('expanded')) {
                        // Logic to expand can be added here if needed
                    }
                } else {
                    province.style.display = 'none';
                }
            });
        });
    }
});
</script>
"""
m.get_root().html.add_child(Element(calibration_html))

# %% Save and open the map
m.save("./mappa.html")
webbrowser.open(f"file://{os.path.abspath('index.html')}")
