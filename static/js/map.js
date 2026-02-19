// static/js/map.js

// 1. 전역 변수 설정 (기존 로직 유지)
let map, vworldKey, baseLayer, satLayer, hybLayer, vectorLayer;
let originalData = null;
let currentFeaturesData = []; 
let currentIndex = -1;       
let overlay, content, closer, regionSearchInput;

// 2. 모바일 바텀 시트 제어 변수
let startY = 0;
let startHeight = 0;
const sidebar = document.getElementById('sidebar');
const handle = document.querySelector('.mobile-handle');
const snapHeights = {
    collapsed: 0.15,
    mid: 0.4,
    expanded: 0.85,
};

// 3. 지도 초기화 함수
function initMap(key, center, zoom) {
    console.log("전달된 좌표:", center); // 브라우저 개발자 도구(F12)에서 확인용
    const commonSource = (type) => new ol.source.XYZ({
        url: `https://api.vworld.kr/req/wmts/1.0.0/${key}/${type}/{z}/{y}/{x}.${type === 'Satellite' ? 'jpeg' : 'png'}`,
        crossOrigin: 'anonymous'
    });

    baseLayer = new ol.layer.Tile({ source: commonSource('Base'), visible: true, zIndex: 0 });
    satLayer = new ol.layer.Tile({ source: commonSource('Satellite'), visible: false, zIndex: 0 });
    hybLayer = new ol.layer.Tile({ source: commonSource('Hybrid'), visible: false, zIndex: 1 });

    map = new ol.Map({
        target: 'map',
        layers: [baseLayer, satLayer, hybLayer],
        overlays: [overlay],
        view: new ol.View({
            center: ol.proj.fromLonLat(center),
            zoom: zoom,
            maxZoom: 22,
            minZoom: 7,
            constrainResolution: false
        })
    });

    map.on('singleclick', (evt) => {
        const feature = map.forEachFeatureAtPixel(evt.pixel, (f) => f);
        if (feature) {
            const idx = feature.getId(); // 설정된 ID로 인덱스 찾기
            if (idx !== undefined) selectItem(idx, false);
            showPopup(feature, evt.coordinate);
        } else {
            overlay.setPosition(undefined);
        }
    });
}

// 4. 모바일 바텀 시트 드래그 이벤트 (터치)
if (handle) {
    handle.addEventListener('touchstart', (e) => {
        startY = e.touches[0].clientY;
        startHeight = sidebar.offsetHeight;
        sidebar.style.transition = 'none'; 
    });

    handle.addEventListener('touchmove', (e) => {
        const touchY = e.touches[0].clientY;
        const deltaY = startY - touchY;
        const newHeight = startHeight + deltaY;

        if (newHeight > window.innerHeight * 0.12 && newHeight < window.innerHeight * 0.9) {
            sidebar.style.height = `${newHeight}px`;
        }
    });

    handle.addEventListener('touchend', () => {
        sidebar.style.transition = 'height 0.3s ease-out';
        const currentRatio = sidebar.offsetHeight / window.innerHeight;
        if (currentRatio >= 0.6) {
            sidebar.style.height = `${snapHeights.expanded * 100}vh`;
        } else if (currentRatio <= 0.25) {
            sidebar.style.height = `${snapHeights.collapsed * 100}vh`;
        } else {
            sidebar.style.height = `${snapHeights.mid * 100}vh`;
        }
    });
}

// 5. 기타 기존 함수들 (loadData, selectItem, navigateItem 등)을 아래에 그대로 옮겨줍니다.
function changeLayer(type) {
    if (map.getView().getZoom() >= 20) map.getView().setZoom(19);
    baseLayer.setVisible(type === 'Base');
    satLayer.setVisible(type === 'Satellite' || type === 'Hybrid');
    hybLayer.setVisible(type === 'Hybrid');
    document.querySelectorAll('.map-controls button').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`btn-${type}`).classList.add('active');
}

function loadLandData() {
    fetch('/api/lands')
        .then(res => res.json())
        .then(data => {
            originalData = data;
            applyFilters();
        })
        .catch((err) => {
            console.error('토지 데이터 로딩 실패:', err);
        });
}

function applyFilters() {
    if (!originalData || !Array.isArray(originalData.features) || !regionSearchInput) {
        return;
    }

    const rentOnlyEl = document.getElementById('rent-only-filter');
    const minAreaEl = document.getElementById('min-area');
    const maxAreaEl = document.getElementById('max-area');
    if (!rentOnlyEl || !minAreaEl || !maxAreaEl) {
        return;
    }

    const isRentOnly = rentOnlyEl.checked;
    const searchTerm = regionSearchInput.value.trim(); // 사용자가 입력한 텍스트
    const minArea = parseFloat(minAreaEl.value) || 0;
    const maxArea = parseFloat(maxAreaEl.value) || Infinity;

    const filteredFeatures = originalData.features.filter(f => {
        const p = f.properties;
        const matchRegion = (searchTerm === '' || p.address.includes(searchTerm));
        const matchArea = (p.area >= minArea && p.area <= maxArea);
        let matchRent = true;
        if (isRentOnly) {
            const isAdmRentable = (p.adm_property && p.adm_property.toLowerCase() === 'o');
            const isGenRentable = (p.gen_property && p.gen_property.startsWith('대부'));
            matchRent = (isAdmRentable || isGenRentable);
        }

        return matchRegion && matchArea && matchRent;
    });

    updateMapAndList({ type: 'FeatureCollection', features: filteredFeatures });
}

function updateMapAndList(data) {
    currentFeaturesData = data.features;
    currentIndex = -1;

    if (vectorLayer) map.removeLayer(vectorLayer);
    
    const vectorSource = new ol.source.Vector();
    const features = new ol.format.GeoJSON().readFeatures(data, { featureProjection: 'EPSG:3857' });
    
    // 핵심: 각 피처에 고유 ID(인덱스) 부여
    features.forEach((f, idx) => {
        f.setId(idx); 
        vectorSource.addFeature(f);
    });

    vectorLayer = new ol.layer.Vector({
        source: vectorSource,
        zIndex: 10,
        style: new ol.style.Style({
            stroke: new ol.style.Stroke({ color: '#ff3333', width: 3 }),
            fill: new ol.style.Fill({ color: 'rgba(255, 51, 51, 0.2)' })
        })
    });
    map.addLayer(vectorLayer);

    const listArea = document.getElementById('list-container');
    listArea.replaceChildren();

    if (!data.features.length) {
        const empty = document.createElement('p');
        empty.style.padding = '20px';
        empty.style.color = 'red';
        empty.textContent = '결과 없음';
        listArea.appendChild(empty);
    }

    data.features.forEach((f, idx) => {
        const item = document.createElement('div');
        item.className = 'list-item';
        item.id = `item-${idx}`;

        const title = document.createElement('strong');
        title.textContent = f.properties.address || '';

        const lineBreak = document.createElement('br');

        const desc = document.createElement('small');
        desc.textContent = `${f.properties.land_type || ''} | ${f.properties.area || ''}㎡`;

        item.appendChild(title);
        item.appendChild(lineBreak);
        item.appendChild(desc);
        item.onclick = () => selectItem(idx);
        listArea.appendChild(item);
    });

    if (data.features.length > 0) {
        // 전체보기 시에도 사이드바 고려 패딩
        map.getView().fit(vectorSource.getExtent(), { padding: [50, 50, 50, 50], duration: 1000 });
    }
    updateNavigationUI();
}

function selectItem(idx, shouldFit = true) {
    if (idx < 0 || idx >= currentFeaturesData.length) return;
    
    currentIndex = idx;
    // ID를 사용하여 정확한 피처를 가져옴
    const feature = vectorLayer.getSource().getFeatureById(idx);
    
    if (feature) {
        const geometry = feature.getGeometry();
        const extent = geometry.getExtent();
        const center = ol.extent.getCenter(extent);

        if (shouldFit) {
            map.getView().fit(extent, { 
                padding: [100, 100, 100, 100], // 상, 우, 하, 좌 (좌측 대폭 확보)
                duration: 800, 
                maxZoom: 19
            });
        }
        
        // 네비게이션 이동 시 팝업 자동 실행
        showPopup(feature, center);
    }

    updateNavigationUI();
    
    const selectedEl = document.getElementById(`item-${idx}`);
    if (selectedEl) {
        selectedEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function showPopup(feature, coordinate) {
    const p = feature.getProperties();
    content.replaceChildren();

    const rows = [
        ['📍 주소', p.address],
        ['📏 면적', `${p.area}㎡`],
        ['📂 지목', p.land_type],
        ['📞 문의', p.contact],
    ];

    rows.forEach(([label, value]) => {
        const line = document.createElement('div');
        line.textContent = `${label}: ${value || ''}`;
        content.appendChild(line);
    });

    overlay.setPosition(coordinate);
}

function navigateItem(direction) {
    const nextIdx = currentIndex + direction;
    if (nextIdx >= 0 && nextIdx < currentFeaturesData.length) {
        selectItem(nextIdx);
    }
}

function updateNavigationUI() {
    const total = currentFeaturesData.length;
    document.getElementById('nav-info').innerText = total > 0 ? `${currentIndex + 1} / ${total}` : '0 / 0';
    document.getElementById('prev-btn').disabled = (currentIndex <= 0);
    document.getElementById('next-btn').disabled = (currentIndex >= total - 1 || total === 0);

    document.querySelectorAll('.list-item').forEach((item, idx) => {
        item.classList.toggle('selected', idx === currentIndex);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    // HTML 요소 할당
    regionSearchInput = document.getElementById('region-search');
    const container = document.getElementById('popup');
    content = document.getElementById('popup-content');
    closer = document.getElementById('popup-closer');
    
    // 오버레이 생성
    overlay = new ol.Overlay({ element: container, autoPan: true, autoPanAnimation: { duration: 250 } });

    // 팝업 닫기 이벤트
    if (closer) {
        closer.onclick = () => { overlay.setPosition(undefined); return false; };
    }

    // 서버 설정값 가져오기 및 초기화
    fetch('/api/config')
        .then(res => res.json())
        .then(config => {
            if (!config.center) return;
            vworldKey = config.vworldKey;
            initMap(vworldKey, config.center, config.zoom);
            loadLandData();
        });

    // 버튼/체크박스 이벤트 연결 (inline handler 제거 대응)
    const searchBtn = document.getElementById('btn-search');
    const rentFilter = document.getElementById('rent-only-filter');
    const btnBase = document.getElementById('btn-Base');
    const btnSatellite = document.getElementById('btn-Satellite');
    const btnHybrid = document.getElementById('btn-Hybrid');
    const prevBtn = document.getElementById('prev-btn');
    const nextBtn = document.getElementById('next-btn');

    if (searchBtn) searchBtn.addEventListener('click', applyFilters);
    if (rentFilter) {
        rentFilter.addEventListener('change', applyFilters);
        rentFilter.addEventListener('click', applyFilters);
    }
    if (btnBase) btnBase.addEventListener('click', () => changeLayer('Base'));
    if (btnSatellite) btnSatellite.addEventListener('click', () => changeLayer('Satellite'));
    if (btnHybrid) btnHybrid.addEventListener('click', () => changeLayer('Hybrid'));
    if (prevBtn) prevBtn.addEventListener('click', () => navigateItem(-1));
    if (nextBtn) nextBtn.addEventListener('click', () => navigateItem(1));

    // 검색창 엔터 이벤트
    if (regionSearchInput) {
        regionSearchInput.addEventListener('keydown', (event) => {
            if (event.key === 'Enter') {
                event.preventDefault();
                applyFilters();
            }
        });
    }
});
