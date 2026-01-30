/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Dashboard pour le profil Gestionnaire OT
 * Focus sur la création et gestion des Ordres de Transit à partir des Contrats
 */
export class PottingOtManagerDashboard extends Component {
    static template = "potting_management.OtManagerDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            // Campagne active
            currentCampaign: null,
            
            // Statistiques OT
            otStats: {
                total: 0,
                draft: 0,
                confirmed: 0,
                formule_linked: 0,
                in_progress: 0,
                ready_validation: 0,
                done: 0,
            },
            
            // Statistiques Allocations OT-Contrats
            allocationStats: {
                total: 0,
                pending: 0,
                fully_allocated: 0,
                partial: 0,
                tonnage_total: 0,
                tonnage_allocated: 0,
            },
            
            // Tonnages globaux
            tonnageStats: {
                contract_total: 0,
                ot_total: 0,
                available: 0,
                percentage_allocated: 0,
            },
            
            // Contrats disponibles pour allocation
            contractsAvailable: [],
            
            // OT récents
            recentOTs: [],
            
            // OT en attente d'allocation
            pendingAllocations: [],
            
            // Allocations actives
            activeAllocations: [],
            
            // Stats par type de produit
            productStats: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        // Charger la campagne active
        try {
            const campaigns = await this.orm.searchRead(
                "potting.campaign",
                [['state', '=', 'active']],
                ["name", "code", "date_start", "date_end", "transit_order_count", "total_tonnage"],
                { limit: 1 }
            );
            if (campaigns.length > 0) {
                this.state.currentCampaign = campaigns[0];
            }
        } catch (e) {
            console.log("Campaign model not available");
        }

        await this.loadOTStats();
        await this.loadAllocationStats();
        await this.loadTonnageStats();
        await this.loadRecentData();
        await this.loadProductStats();
    }

    async loadOTStats() {
        try {
            // Total des OT
            this.state.otStats.total = await this.orm.searchCount(
                "potting.transit.order", []
            );

            // OT par état
            const states = ['draft', 'confirmed', 'formule_linked', 'in_progress', 'ready_validation', 'done'];
            for (const state of states) {
                this.state.otStats[state] = await this.orm.searchCount(
                    "potting.transit.order",
                    [['state', '=', state]]
                );
            }
        } catch (e) {
            console.error("Error loading OT stats:", e);
        }
    }

    async loadAllocationStats() {
        try {
            // Total des allocations OT-Contrats
            this.state.allocationStats.total = await this.orm.searchCount(
                "potting.ot.contract.allocation", []
            );

            // Allocations par état
            const allocations = await this.orm.searchRead(
                "potting.ot.contract.allocation",
                [],
                ["tonnage_alloue", "state"]
            );

            this.state.allocationStats.tonnage_total = allocations.reduce(
                (sum, a) => sum + (a.tonnage_alloue || 0), 0
            );

            // Comptage par état (si le champ state existe)
            const pendingCount = allocations.filter(a => !a.state || a.state === 'draft').length;
            const activeCount = allocations.filter(a => a.state === 'active').length;
            
            this.state.allocationStats.pending = pendingCount;
            this.state.allocationStats.fully_allocated = activeCount;
        } catch (e) {
            console.log("Allocation stats not available:", e);
        }
    }

    async loadTonnageStats() {
        try {
            // Tonnage total des contrats
            const contracts = await this.orm.searchRead(
                "potting.customer.order",
                [['state', 'not in', ['cancelled', 'done']]],
                ["contract_tonnage", "remaining_contract_tonnage"]
            );

            this.state.tonnageStats.contract_total = contracts.reduce(
                (sum, c) => sum + (c.contract_tonnage || 0), 0
            );
            
            const remaining = contracts.reduce(
                (sum, c) => sum + (c.remaining_contract_tonnage || 0), 0
            );
            this.state.tonnageStats.available = remaining;

            // Tonnage total des OT
            const ots = await this.orm.searchRead(
                "potting.transit.order",
                [['state', 'not in', ['cancelled']]],
                ["tonnage"]
            );

            this.state.tonnageStats.ot_total = ots.reduce(
                (sum, ot) => sum + (ot.tonnage || 0), 0
            );

            // Pourcentage alloué
            if (this.state.tonnageStats.contract_total > 0) {
                this.state.tonnageStats.percentage_allocated = 
                    (this.state.tonnageStats.ot_total / this.state.tonnageStats.contract_total) * 100;
            }
        } catch (e) {
            console.error("Error loading tonnage stats:", e);
        }
    }

    async loadRecentData() {
        try {
            // OT récents
            this.state.recentOTs = await this.orm.searchRead(
                "potting.transit.order",
                [['state', 'in', ['draft', 'confirmed', 'formule_linked']]],
                ["name", "customer_order_id", "consignee_id", "product_type", "tonnage", "state", "create_date"],
                { limit: 10, order: "create_date desc" }
            );

            // Contrats disponibles pour allocation
            this.state.contractsAvailable = await this.orm.searchRead(
                "potting.customer.order",
                [
                    ['state', 'in', ['confirmed', 'in_progress']],
                    ['remaining_contract_tonnage', '>', 0]
                ],
                ["name", "customer_id", "contract_tonnage", "remaining_contract_tonnage", "product_type"],
                { limit: 10, order: "remaining_contract_tonnage desc" }
            );

            // Allocations actives
            this.state.activeAllocations = await this.orm.searchRead(
                "potting.ot.contract.allocation",
                [],
                ["transit_order_id", "customer_order_id", "tonnage_alloue", "create_date"],
                { limit: 10, order: "create_date desc" }
            );
        } catch (e) {
            console.error("Error loading recent data:", e);
        }
    }

    async loadProductStats() {
        try {
            const ots = await this.orm.searchRead(
                "potting.transit.order",
                [['state', 'not in', ['cancelled']]],
                ["product_type", "tonnage"]
            );

            const productMap = {};
            for (const ot of ots) {
                const ptype = ot.product_type || 'unknown';
                if (!productMap[ptype]) {
                    productMap[ptype] = { type: ptype, count: 0, tonnage: 0 };
                }
                productMap[ptype].count++;
                productMap[ptype].tonnage += ot.tonnage || 0;
            }

            this.state.productStats = Object.values(productMap).sort(
                (a, b) => b.tonnage - a.tonnage
            );
        } catch (e) {
            console.error("Error loading product stats:", e);
        }
    }

    // ============ Actions ============

    createOT() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Nouvel OT',
            res_model: 'potting.transit.order',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openCreateOTWizard() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Créer OT depuis Contrat',
            res_model: 'potting.generate.ot.from.order.wizard',
            views: [[false, 'form']],
            target: 'new',
        });
    }

    openOTs(state = null) {
        const domain = state ? [['state', '=', state]] : [];
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Ordres de Transit',
            res_model: 'potting.transit.order',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: domain,
            context: {},
        });
    }

    openAllocations() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Allocations OT-Contrats',
            res_model: 'potting.ot.contract.allocation',
            views: [[false, 'list'], [false, 'form']],
            context: {},
        });
    }

    openContracts() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Contrats disponibles',
            res_model: 'potting.customer.order',
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['state', 'in', ['confirmed', 'in_progress']],
                ['remaining_contract_tonnage', '>', 0]
            ],
            context: {},
        });
    }

    openOT(otId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'potting.transit.order',
            res_id: otId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openContract(contractId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'potting.customer.order',
            res_id: contractId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openCampaigns() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Campagnes',
            res_model: 'potting.campaign',
            views: [[false, 'list'], [false, 'form']],
            context: {},
        });
    }

    // ============ Formatters ============

    formatNumber(value, decimals = 0) {
        if (value === null || value === undefined) return '0';
        return parseFloat(value).toLocaleString('fr-FR', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        });
    }

    formatCurrency(value) {
        if (value === null || value === undefined) return '0';
        return parseFloat(value).toLocaleString('fr-FR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        });
    }

    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR');
    }

    getProductTypeLabel(type) {
        const labels = {
            'masse': 'Masse de cacao',
            'beurre': 'Beurre de cacao',
            'tourteau': 'Tourteau/Cake',
            'poudre': 'Poudre de cacao',
            'unknown': 'Non défini',
        };
        return labels[type] || type;
    }

    getStateLabel(state) {
        const labels = {
            'draft': 'Brouillon',
            'confirmed': 'Confirmé',
            'formule_linked': 'Formule liée',
            'in_progress': 'En production',
            'ready_validation': 'Prêt validation',
            'done': 'Terminé',
        };
        return labels[state] || state;
    }

    getStateBadgeClass(state) {
        const classes = {
            'draft': 'badge bg-secondary',
            'confirmed': 'badge bg-info',
            'formule_linked': 'badge bg-primary',
            'in_progress': 'badge bg-warning',
            'ready_validation': 'badge bg-info',
            'done': 'badge bg-success',
        };
        return classes[state] || 'badge bg-secondary';
    }
}

// Register the client action
registry.category("actions").add("potting_ot_manager_dashboard", PottingOtManagerDashboard);
