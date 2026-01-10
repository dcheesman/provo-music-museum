// Velour Live Artist Network Visualization
// Using D3.js for interactive network graph

let data = null;
let simulation = null;
let svg = null;
let g = null;
let tooltip = null;
let linkTooltip = null;
let selectedNode = null;

// Configuration
const config = {
    nodeSize: 3,
    linkDistance: 50,
    charge: -100,
    width: window.innerWidth - 40,
    height: window.innerHeight * 0.8
};

// Initialize
async function init() {
    // Set up SVG
    svg = d3.select("#network")
        .attr("width", config.width)
        .attr("height", config.height);
    
    g = svg.append("g");
    
    // Set up tooltips
    tooltip = d3.select("#tooltip");
    linkTooltip = d3.select("#linkTooltip");
    
    // Load data
    try {
        // Try local file first (copied to webapp directory), then relative path
        let response = await fetch('network_data.json');
        if (!response.ok) {
            // Fallback to relative path
            response = await fetch('../data/processed/artist_network_enhanced_20260102_211457.json');
        }
        if (!response.ok) {
            // Fallback to regular network file
            response = await fetch('../data/processed/artist_network_20260102_211457.json');
        }
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}. Make sure the web server is running.`);
        }
        data = await response.json();
        
        // Update stats
        document.getElementById('nodeCount').textContent = `${data.nodes.length} Artists`;
        document.getElementById('linkCount').textContent = `${data.edges.length} Connections`;
        
        // Filter to top artists for better performance (optional)
        // Start with a reasonable filter to avoid overwhelming the browser
        filterTopArtists(3);
        
        // Set up controls
        setupControls();
        
        // Create visualization
        createVisualization();
    } catch (error) {
        console.error('Error loading data:', error);
        console.error('Error details:', error.message);
        alert(`Error loading network data.\n\n${error.message}\n\nPlease check:\n1. The web server is running\n2. The data file exists at: ../data/processed/artist_network_enhanced_20260102_211457.json\n3. Check browser console (F12) for more details`);
    }
}

function filterTopArtists(minShows = 5) {
    if (!data) return;
    
    // Filter nodes by show count
    const topNodes = data.nodes.filter(node => node.shows >= minShows);
    const topNodeIds = new Set(topNodes.map(n => n.id));
    
    // Filter edges to only include connections between top nodes
    // Also map source/target to node objects if they're IDs
    const topEdges = data.edges
        .filter(edge => {
            const sourceId = typeof edge.source === 'object' ? edge.source.id : edge.source;
            const targetId = typeof edge.target === 'object' ? edge.target.id : edge.target;
            return topNodeIds.has(sourceId) && topNodeIds.has(targetId);
        })
        .map(edge => {
            // Ensure source and target are IDs (not objects)
            return {
                ...edge,
                source: typeof edge.source === 'object' ? edge.source.id : edge.source,
                target: typeof edge.target === 'object' ? edge.target.id : edge.target
            };
        });
    
    data = {
        nodes: topNodes,
        edges: topEdges,
        metadata: data.metadata
    };
    
    // Update stats
    document.getElementById('nodeCount').textContent = `${data.nodes.length} Artists`;
    document.getElementById('linkCount').textContent = `${data.edges.length} Connections`;
}

function setupControls() {
    // Node size slider
    const nodeSizeSlider = document.getElementById('nodeSizeSlider');
    const nodeSizeValue = document.getElementById('nodeSizeValue');
    
    nodeSizeSlider.addEventListener('input', (e) => {
        config.nodeSize = parseFloat(e.target.value);
        nodeSizeValue.textContent = config.nodeSize;
        updateNodeSizes();
    });
    
    // Link distance slider
    const linkDistanceSlider = document.getElementById('linkDistanceSlider');
    const linkDistanceValue = document.getElementById('linkDistanceValue');
    
    linkDistanceSlider.addEventListener('input', (e) => {
        config.linkDistance = parseInt(e.target.value);
        linkDistanceValue.textContent = config.linkDistance;
                if (simulation) {
                    simulation.force('link').distance(config.linkDistance);
                    simulation.alpha(0.3).restart();  // Start with lower alpha for smoother transitions
                }
    });
    
    // Charge slider
    const chargeSlider = document.getElementById('chargeSlider');
    const chargeValue = document.getElementById('chargeValue');
    
    chargeSlider.addEventListener('input', (e) => {
        config.charge = parseInt(e.target.value);
        chargeValue.textContent = config.charge;
                if (simulation) {
                    simulation.force('charge').strength(config.charge);
                    simulation.alpha(0.3).restart();  // Start with lower alpha for smoother transitions
                }
    });
    
    // Reset button
    document.getElementById('resetButton').addEventListener('click', () => {
        if (simulation) {
            data.nodes.forEach(node => {
                node.fx = null;
                node.fy = null;
            });
            simulation.alpha(0.3).restart();  // Start with lower alpha for smoother transitions
        }
        selectedNode = null;
        updateVisualization();
    });
    
    // Filter button
    document.getElementById('filterButton').addEventListener('click', () => {
        const minShows = prompt('Enter minimum number of shows (default: 5):', '5');
        if (minShows !== null) {
            // Reload original data
            loadOriginalData().then(() => {
                filterTopArtists(parseInt(minShows) || 5);
                createVisualization();
            });
        }
    });
    
    // Relax button - let network settle more
    document.getElementById('relaxButton').addEventListener('click', () => {
        if (simulation) {
            console.log('Relaxing network for better layout...');
            simulation.alpha(0.5).restart();
            document.getElementById('relaxButton').textContent = 'Relaxing...';
            setTimeout(() => {
                document.getElementById('relaxButton').textContent = 'Relax Network';
            }, 5000);
        }
    });
}

async function loadOriginalData() {
    let response = await fetch('network_data.json');
    if (!response.ok) {
        response = await fetch('../data/processed/artist_network_enhanced_20260102_211457.json');
    }
    if (!response.ok) {
        response = await fetch('../data/processed/artist_network_20260102_211457.json');
    }
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    data = await response.json();
}

function createVisualization() {
    if (!data || !data.nodes || !data.edges) {
        console.error('Invalid data structure');
        return;
    }
    
    // Clear existing visualization
    g.selectAll("*").remove();
    
    // Create zoom behavior
    const zoom = d3.zoom()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
            g.attr("transform", event.transform);
        });
    
    svg.call(zoom);
    
    // Create links
    const link = g.append("g")
        .attr("class", "links")
        .selectAll("line")
        .data(data.edges)
        .enter()
        .append("line")
        .attr("class", "link")
        .attr("stroke-width", d => Math.sqrt(d.weight) * 0.5)
        .on("mouseover", function(event, d) {
            showLinkTooltip(event, d);
        })
        .on("mouseout", hideLinkTooltip);
    
    // Create nodes
    const node = g.append("g")
        .attr("class", "nodes")
        .selectAll("circle")
        .data(data.nodes)
        .enter()
        .append("circle")
        .attr("class", "node")
        .attr("r", d => Math.sqrt(d.shows) * config.nodeSize)
        .attr("fill", d => getNodeColor(d.shows))
        .call(drag(simulation))
        .on("mouseover", function(event, d) {
            showNodeTooltip(event, d);
            highlightNode(d);
        })
        .on("mouseout", function() {
            hideNodeTooltip();
            unhighlightNode();
        })
        .on("click", function(event, d) {
            selectNode(d);
        });
    
    // Create labels (optional, can be toggled)
    const label = g.append("g")
        .attr("class", "labels")
        .selectAll("text")
        .data(data.nodes.filter(d => d.shows >= 10)) // Only show labels for artists with 10+ shows
        .enter()
        .append("text")
        .attr("class", "node-label")
        .text(d => d.label)
        .attr("dx", 0)
        .attr("dy", d => Math.sqrt(d.shows) * config.nodeSize + 15);
    
    // Create simulation with longer settling time
    simulation = d3.forceSimulation(data.nodes)
        .force("link", d3.forceLink(data.edges).id(d => d.id)
            .distance(config.linkDistance)
            .strength(0.5))
        .force("charge", d3.forceManyBody().strength(config.charge))
        .force("center", d3.forceCenter(config.width / 2, config.height / 2))
        .force("collision", d3.forceCollide().radius(d => Math.sqrt(d.shows) * config.nodeSize + 5))
        .alphaDecay(0.01)  // Slower decay = runs longer (default is 0.0228)
        .alphaTarget(0.001)  // Keep running until very low energy
        .velocityDecay(0.4);  // More friction for smoother settling (default is 0.4)
    
    // Update positions on tick
    let tickCount = 0;
    simulation.on("tick", () => {
        tickCount++;
        
        link
            .attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);
        
        node
            .attr("cx", d => d.x)
            .attr("cy", d => d.y);
        
        label
            .attr("x", d => d.x)
            .attr("y", d => d.y);
        
        // Log progress every 100 ticks
        if (tickCount % 100 === 0) {
            const alpha = simulation.alpha();
            if (alpha > 0.001) {
                console.log(`Simulation running... alpha: ${alpha.toFixed(4)}, ticks: ${tickCount}`);
            }
        }
    });
    
    // Keep simulation running longer - restart if it stops too early
    simulation.on("end", () => {
        const alpha = simulation.alpha();
        if (alpha > 0.001 && tickCount < 1000) {
            // Restart if it stopped too early
            console.log("Restarting simulation for better settling...");
            simulation.alpha(0.3).restart();
        } else {
            console.log(`Simulation settled after ${tickCount} ticks`);
        }
    });
}

function updateNodeSizes() {
    g.selectAll(".node")
        .attr("r", d => Math.sqrt(d.shows) * config.nodeSize);
    
    if (simulation) {
        simulation.force("collision")
            .radius(d => Math.sqrt(d.shows) * config.nodeSize + 5);
        simulation.alpha(0.3).restart();  // Start with lower alpha for smoother transitions
    }
}

function getNodeColor(shows) {
    // Color scale based on number of shows
    if (shows >= 20) return "#e74c3c";      // Red for very active
    if (shows >= 10) return "#f39c12";      // Orange for active
    if (shows >= 5) return "#3498db";        // Blue for moderately active
    return "#95a5a6";                        // Gray for less active
}

function showNodeTooltip(event, d) {
    tooltip
        .html(`
            <h3>${d.label}</h3>
            <p><strong>Shows:</strong> ${d.shows}</p>
            <p><strong>Connections:</strong> ${getConnectionCount(d.id)}</p>
        `)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 10) + "px")
        .classed("visible", true);
}

function hideNodeTooltip() {
    tooltip.classed("visible", false);
}

function showLinkTooltip(event, d) {
    const shows = d.shows || [];
    const totalShows = d.total_shows || d.weight || 0;
    
    // Get source and target labels - handle both string IDs and object references
    let sourceLabel, targetLabel;
    
    if (typeof d.source === 'string') {
        sourceLabel = getNodeLabel(d.source);
    } else if (d.source && d.source.label) {
        sourceLabel = d.source.label;
    } else if (d.source && d.source.id) {
        sourceLabel = getNodeLabel(d.source.id);
    } else {
        sourceLabel = 'Unknown';
    }
    
    if (typeof d.target === 'string') {
        targetLabel = getNodeLabel(d.target);
    } else if (d.target && d.target.label) {
        targetLabel = d.target.label;
    } else if (d.target && d.target.id) {
        targetLabel = getNodeLabel(d.target.id);
    } else {
        targetLabel = 'Unknown';
    }
    
    let html = `<h3>${sourceLabel} ↔ ${targetLabel}</h3>`;
    html += `<p><strong>Shows Together:</strong> ${totalShows}</p>`;
    
    if (shows.length > 0) {
        html += `<div style="max-height: 200px; overflow-y: auto;">`;
        shows.forEach(show => {
            html += `<div class="show-item">`;
            html += `<strong>${show.date || 'Date unknown'}</strong><br>`;
            html += `${show.title || show.description || 'Show'}`;
            if (show.genre) {
                html += `<br><em>${show.genre}</em>`;
            }
            html += `</div>`;
        });
        if (totalShows > shows.length) {
            html += `<p><em>... and ${totalShows - shows.length} more shows</em></p>`;
        }
        html += `</div>`;
    }
    
    linkTooltip
        .html(html)
        .style("left", (event.pageX + 10) + "px")
        .style("top", (event.pageY - 10) + "px")
        .classed("visible", true);
}

function hideLinkTooltip() {
    linkTooltip.classed("visible", false);
}

function getNodeLabel(id) {
    // Handle if id is already an object with a label
    if (typeof id === 'object' && id !== null) {
        if (id.label) return id.label;
        if (id.id) id = id.id;
    }
    
    // Now id should be a string
    if (typeof id === 'string') {
        const node = data.nodes.find(n => n.id === id);
        if (node && node.label) {
            return node.label;
        }
        // Fallback to id if no node found
        return id;
    }
    
    return 'Unknown';
}

function getConnectionCount(nodeId) {
    return data.edges.filter(e => {
        const sourceId = typeof e.source === 'object' ? e.source.id : e.source;
        const targetId = typeof e.target === 'object' ? e.target.id : e.target;
        return sourceId === nodeId || targetId === nodeId;
    }).length;
}

function highlightNode(d) {
    const nodeId = d.id;
    
    g.selectAll(".link")
        .classed("faded", link => {
            const sourceId = typeof link.source === 'object' ? link.source.id : link.source;
            const targetId = typeof link.target === 'object' ? link.target.id : link.target;
            return sourceId !== nodeId && targetId !== nodeId;
        });
    
    g.selectAll(".node")
        .classed("faded", node => {
            if (node.id === nodeId) return false;
            return !data.edges.some(e => {
                const eSourceId = typeof e.source === 'object' ? e.source.id : e.source;
                const eTargetId = typeof e.target === 'object' ? e.target.id : e.target;
                return (eSourceId === nodeId && eTargetId === node.id) ||
                       (eTargetId === nodeId && eSourceId === node.id);
            });
        });
}

function unhighlightNode() {
    g.selectAll(".link").classed("faded", false);
    g.selectAll(".node").classed("faded", false);
}

function selectNode(d) {
    // Deselect previous
    if (selectedNode) {
        selectedNode = null;
    } else {
        selectedNode = d;
    }
    
    updateVisualization();
}

function updateVisualization() {
    g.selectAll(".node")
        .classed("selected", d => selectedNode && d.id === selectedNode.id);
    
    if (selectedNode) {
        highlightNode(selectedNode);
    } else {
        unhighlightNode();
    }
}

function drag(simulation) {
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }
    
    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }
    
    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        // Uncomment to allow nodes to move freely after drag
        // d.fx = null;
        // d.fy = null;
    }
    
    return d3.drag()
        .on("start", dragstarted)
        .on("drag", dragged)
        .on("end", dragended);
}

// Handle window resize
window.addEventListener('resize', () => {
    config.width = window.innerWidth - 40;
    config.height = window.innerHeight * 0.8;
    
    svg.attr("width", config.width).attr("height", config.height);
    
    if (simulation) {
        simulation.force("center", d3.forceCenter(config.width / 2, config.height / 2));
        simulation.alpha(1).restart();
    }
});

// Initialize on load
init();

