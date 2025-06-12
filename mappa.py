# %%
import geopandas as gpd
import folium
from folium import GeoJson, Element
import json
import webbrowser
import os
import unicodedata
import re


# %% Funzione di utilità: normalizza le stringhe (rimuove accenti e parentesi)
def normalize_string(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")  # Rimuove accenti
    return re.sub(r"[()]", "", s).strip().lower()  # Rimuove parentesi


# %% Restituisce un colore per ogni provincia (usato per il bordo sinistro)
def get_province_color(province_code):
    color_map = {
        81: "#FFB400",  # Oro
        84: "#FF6F61",  # Corallo
        85: "#9370DB",  # Viola
        86: "#E9967A",  # Salmone
        88: "#708090",  # Grigio
        89: "#D9534F",  # Rosso
        280: "#00A86B", # Verde
        282: "#4682B4", # Blu
        283: "#40E0D0", # Turchese
        287: "#9932CC", # Viola scuro
    }
    return color_map.get(province_code, "#2F4F4F")  # Default: grigio scuro


# %% Carica i dati geografici dei comuni e delle province
data_path = "../finaiti/basidati.gpkg"
map_data = gpd.read_file(data_path, layer="cumuna")
provinces = gpd.read_file(data_path, layer="pruvinci")

# %% Crea una mappatura codice provincia -> nome provincia
province_mapping = {row["COD_UTS"]: row["SCN"] for _, row in provinces.iterrows()}

# %% Crea la mappa Folium centrata sulla Sicilia
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
)

# %% Collega il foglio di stile CSS esterno
m.get_root().html.add_child(
    folium.Element(
        """
<link rel="stylesheet" type="text/css" href="css/map-styles.css">"""
    )
)

# %% Espone la variabile mappa come window.map per JS
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

# %% Funzioni JS globali per interazione e highlight
# (gestione selezione, info, label, ecc.)
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
    // Mostra/nasconde info nella barra laterale
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
            // Scrolla la barra laterale per mostrare le info
            var searchContainer = document.querySelector(".search-container");
            var searchHeight = searchContainer ? searchContainer.offsetHeight : 60;
            var offset = 75 + searchHeight;
            sidebar.scrollTo({ top: infoDiv.offsetTop - offset, behavior: "smooth" });
        } else {
            infoDiv.style.display = "none";
        }
    }
    // Espande la lista dei comuni di una provincia
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
                    var searchContainer = document.querySelector(".search-container");
                    var searchHeight = searchContainer ? searchContainer.offsetHeight : 60;
                    var offset = 75 + searchHeight;
                    sidebar.scrollTo({ top: infoElem.offsetTop - offset, behavior: "smooth" });
                }, 400);
            }
        }
    }
    // Mostra etichetta con freccia sulla mappa
    function showLabelWithLine(id, name, lat, lon, geometry = null) {
        window.currentLabelData = {id: id, name: name, lat: lat, lon: lon};
        if (window.arrowUI) {
            window.arrowUI.showArrow(id, name, lat, lon, geometry);
        }
    }
    // Mostra etichetta dalla barra laterale
    function showLabelFromSidebar(layer_id) {
        var coords = window.layer_coordinates[layer_id];
        if (coords) {
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
    // Impostazioni globali per la calibrazione
    window.labelSettings = {
        distanceMultiplier: 1.0,
        fontSizeMultiplier: 1.0
    };
    // Inizializza Arrow UI quando la mappa è pronta
    document.addEventListener("DOMContentLoaded", function() {
        setTimeout(function() {
            if (window.ArrowUI && window.map) {
                window.arrowUI = new window.ArrowUI(window.map);
                console.log("Sistema Arrow UI inizializzato!");
            }
        }, 500);
    });
    // Colora dinamicamente il bordo delle province
    document.addEventListener("DOMContentLoaded", function() {
        var provinceBlocks = document.querySelectorAll(".province-block");
        provinceBlocks.forEach(function(block) {
            var color = block.getAttribute("data-province-color");
            if (color) {
                block.style.borderLeftColor = color;
            }
        });
    });
    console.log("Funzioni JS globali definite.");
</script>
"""
m.get_root().html.add_child(Element(global_js))

# %% Prepara la struttura HTML della barra laterale e i dati JS
layer_info_dict = {}
layer_coordinates = {}
locations_html = "<ul id='location-list'>"

grouped = map_data.groupby("COD_UTS")
# Ordina le province alfabeticamente
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

    # Ciclo su tutti i comuni della provincia
    for idx, row in group_sorted.iterrows():
        layer_id = f"layer_{idx}"
        local_name = row["LUCALI"] if row["LUCALI"] != row["SCN"] else None

        # Crea il box info per il comune
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

        # Salva coordinate per click dalla barra laterale
        centroid = row.geometry.centroid
        layer_coordinates[layer_id] = {
            "lat": centroid.y,
            "lon": centroid.x,
            "name": row["SCN"] if row["SCN"] else "?",
        }

        # Elemento della lista (comune)
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

        # Crea layer GeoJson per il comune
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

        # Collega eventi JS al layer
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

    # Blocco provincia con lista comuni
    locations_html += f"""
    <li class="province-block" style="border-left: 6px solid {province_color};">
        <span class="province-header">{province_name}</span>
        <ul class="places-list" style="max-height: 0; overflow: hidden; transition: max-height 0.4s ease-out;">
            {''.join(place_items_html)}
        </ul>
    </li>
    """

locations_html += "</ul>"

# %% Inietta info e coordinate dei layer in JS globale
js_layer_info = f"<script>window.layer_info = {json.dumps(layer_info_dict)};</script>"
js_layer_coordinates = (
    f"<script>window.layer_coordinates = {json.dumps(layer_coordinates)};</script>"
)
m.get_root().html.add_child(Element(js_layer_info))
m.get_root().html.add_child(Element(js_layer_coordinates))

# %% JS per espansione/collasso delle province
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

# %% Include libreria Turf.js per calcoli geometrici
# (usata per trovare il punto interno ai poligoni)
turf_script = """
<script src="https://unpkg.com/@turf/turf@6/turf.min.js"></script>
"""
m.get_root().html.add_child(Element(turf_script))

# %% Sistema Arrow UI: gestisce frecce e label sulla mappa
arrow_ui_script = """
<script>
// Classe ArrowUI: disegna frecce e testo vicino ai comuni
class ArrowUI {
    constructor(map) {
        this.map = map;
        this.currentArrow = null;
        this.currentLabel = null;
        this.currentGeometry = null;
        this.currentStartPoint = null; // Punto di partenza
        this.currentAngle = null; // Angolo fisso
        this.settings = {
            distanceMultiplier: 1.0,
            fontSizeMultiplier: 1.0
        };
        // Aggiorna la freccia quando cambia lo zoom
        this.map.on('zoomend', () => {
            if (this.currentStartPoint && this.currentAngle !== null) {
                this.updateArrowForZoom();
            }
        });
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
            const centroid = turf.centroid(geometry);
            if (turf.booleanPointInPolygon(centroid, geometry)) {
                return [centroid.geometry.coordinates[1], centroid.geometry.coordinates[0]];
            }
            const polylabel = turf.polylabel(geometry);
            return [polylabel.geometry.coordinates[1], polylabel.geometry.coordinates[0]];
        } catch (error) {
            // Fallback: centroide o bbox
            const bbox = turf.bbox(geometry);
            const centerLat = (bbox[1] + bbox[3]) / 2;
            const centerLon = (bbox[0] + bbox[2]) / 2;
            const centerPoint = turf.point([centerLon, centerLat]);
            if (turf.booleanPointInPolygon(centerPoint, geometry)) {
                return [centerLat, centerLon];
            }
            try {
                const polylabel = turf.polylabel(geometry);
                return [polylabel.geometry.coordinates[1], polylabel.geometry.coordinates[0]];
            } catch (e) {
                const centroid = turf.centroid(geometry);
                return [centroid.geometry.coordinates[1], centroid.geometry.coordinates[0]];
            }
        }
    }
    // Mostra la freccia e il testo
    showArrow(id, name, lat, lon, geometry = null) {
        this.currentArrowData = {id, name, lat, lon};
        this.currentGeometry = geometry;
        if (geometry) {
            this.currentStartPoint = this.findInteriorPoint(geometry);
        } else {
            this.currentStartPoint = [lat, lon];
        }
        this.calculateFixedAngle();
        this.drawStraightLine(name);
    }
    // Calcola l'angolo fisso verso sud-ovest
    calculateFixedAngle() {
        const [lat, lon] = this.currentStartPoint;
        this.currentAngle = -Math.PI * 3/4 + (Math.random() - 0.5) * Math.PI/6; // -135° ± 15°
    }
    // Aggiorna la freccia quando cambia lo zoom
    updateArrowForZoom() {
        if (this.currentStartPoint && this.currentAngle !== null) {
            this.drawStraightLine(this.currentArrowData.name);
        }
    }
    // Disegna la linea e il testo
    drawStraightLine(name) {
        this.clearArrow();
        const [startLat, startLon] = this.currentStartPoint;
        const currentZoom = this.map.getZoom();
        const baseZoom = 8;
        const zoomFactor = Math.pow(2, baseZoom - currentZoom);
        const baseLineLength = 0.425 * zoomFactor;
        const adjustedLength = baseLineLength * this.settings.distanceMultiplier;
        const textGap = 0.09 * zoomFactor;
        const textLat = startLat + (adjustedLength + textGap) * Math.sin(this.currentAngle);
        const textLon = startLon + (adjustedLength + textGap) * Math.cos(this.currentAngle);
        const lineStopGap = 0.04 * zoomFactor;
        const lineEndLat = startLat + (adjustedLength + lineStopGap) * Math.sin(this.currentAngle);
        const lineEndLon = startLon + (adjustedLength + lineStopGap) * Math.cos(this.currentAngle);
        this.currentArrow = L.polyline([
            [startLat, startLon],
            [lineEndLat, lineEndLon]
        ], {
            color: '#2C3E50',
            weight: 3,
            opacity: 0.9,
            lineCap: 'round'
        }).addTo(this.map);
        const screenFontSize = 22;
        const adjustedFontSize = screenFontSize * this.settings.fontSizeMultiplier;
        const approxTextWidth = name.length * adjustedFontSize * 0.6;
        const approxTextHeight = adjustedFontSize;
        const labelIcon = L.divIcon({
            className: 'simple-place-label',
            html: `<div class="place-label-text" style="font-size: ${adjustedFontSize}px;">${name}</div>`,
            iconAnchor: [approxTextWidth / 2, approxTextHeight / 2]
        });
        this.currentLabel = L.marker([textLat, textLon], {
            icon: labelIcon,
            zIndexOffset: 1000
        }).addTo(this.map);
        // Effetto hover sulla linea
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
    // Rimuove la freccia e il testo
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

# %% HTML della barra laterale
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

# %% Pannello di calibrazione (in basso a sinistra)
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
        // Aggiorna la distanza della freccia
        distanceSlider.addEventListener("input", function() {
        var value = parseFloat(this.value);
        window.labelSettings.distanceMultiplier = value;
        distanceValue.textContent = value.toFixed(1) + "x";
        if (window.arrowUI) {
            window.arrowUI.updateSettings({distanceMultiplier: value});
        }
    });
    // Aggiorna la grandezza del testo
    fontSlider.addEventListener("input", function() {
        var value = parseFloat(this.value);
        window.labelSettings.fontSizeMultiplier = value;
        fontValue.textContent = value.toFixed(1) + "x";
        if (window.arrowUI) {
            window.arrowUI.updateSettings({fontSizeMultiplier: value});
        }
    });
    // Logica ricerca: filtra comuni in base all'input
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
                    const placesList = province.querySelector('.places-list');
                    if (placesList && !placesList.classList.contains('expanded')) {
                        // Espansione automatica opzionale
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

# %% Salva la mappa e apre index.html
m.save("./mappa.html")
webbrowser.open(f"file://{os.path.abspath('index.html')}")
