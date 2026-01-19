/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Dashboard pour le profil Utilisateur de base
 * Vue simplifiée en lecture seule avec les informations essentielles
 */
export class PottingUserDashboard extends Component {
    static template = "potting_management.UserDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            // Campagne active
            currentCampaign: null,
            
            // Résumé global
            summary: {
                total_contracts: 0,
                total_ot: 0,
                total_lots: 0,
                total_tonnage: 0,
            },
            
            // OT par état (lecture)
            otStats: {
                draft: 0,
                in_progress: 0,
                done: 0,
            },
            
            // Lots par état (lecture)
            lotStats: {
                in_production: 0,
                ready: 0,
                potted: 0,
            },
            
            // OT récents
            recentOT: [],
            
            // Lots récents
            recentLots: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        await this.loadCampaign();
        await this.loadSummary();
        await this.loadOTStats();
        await this.loadLotStats();
        await this.loadRecentItems();
    }

    async loadCampaign() {
        try {
            const campaigns = await this.orm.searchRead(
                "potting.campaign",
                [['state', '=', 'active']],
                ["name", "code", "date_start", "date_end"],
                { limit: 1 }
            );
            if (campaigns.length > 0) {
                this.state.currentCampaign = campaigns[0];
            }
        } catch (e) {
            console.log("Campaign model not available");
        }
    }

    async loadSummary() {
        try {
            this.state.summary.total_contracts = await this.orm.searchCount(
                "potting.customer.order",
                [['state', 'not in', ['cancelled']]]
            );
            
            this.state.summary.total_ot = await this.orm.searchCount(
                "potting.transit.order",
                [['state', 'not in', ['cancelled']]]
            );
            
            this.state.summary.total_lots = await this.orm.searchCount(
                "potting.lot", []
            );

            // Tonnage total
            const lots = await this.orm.searchRead(
                "potting.lot",
                [['state', '=', 'potted']],
                ["current_tonnage"]
            );
            this.state.summary.total_tonnage = lots.reduce(
                (sum, l) => sum + (l.current_tonnage || 0), 0
            );
        } catch (e) {
            console.log("Error loading summary:", e);
        }
    }

    async loadOTStats() {
        try {
            this.state.otStats.draft = await this.orm.searchCount(
                "potting.transit.order",
                [['state', 'in', ['draft', 'lots_generated']]]
            );
            this.state.otStats.in_progress = await this.orm.searchCount(
                "potting.transit.order",
                [['state', 'in', ['in_progress', 'ready_validation']]]
            );
            this.state.otStats.done = await this.orm.searchCount(
                "potting.transit.order",
                [['state', '=', 'done']]
            );
        } catch (e) {
            console.log("Error loading OT stats:", e);
        }
    }

    async loadLotStats() {
        try {
            this.state.lotStats.in_production = await this.orm.searchCount(
                "potting.lot",
                [['state', '=', 'in_production']]
            );
            this.state.lotStats.ready = await this.orm.searchCount(
                "potting.lot",
                [['state', '=', 'ready']]
            );
            this.state.lotStats.potted = await this.orm.searchCount(
                "potting.lot",
                [['state', '=', 'potted']]
            );
        } catch (e) {
            console.log("Error loading lot stats:", e);
        }
    }

    async loadRecentItems() {
        try {
            // OT récents
            this.state.recentOT = await this.orm.searchRead(
                "potting.transit.order",
                [],
                ["reference", "state", "total_tonnage", "customer_id", "create_date"],
                { limit: 5, order: "create_date desc" }
            );

            // Lots récents
            this.state.recentLots = await this.orm.searchRead(
                "potting.lot",
                [],
                ["name", "state", "current_tonnage", "product_type", "create_date"],
                { limit: 5, order: "create_date desc" }
            );
        } catch (e) {
            console.log("Error loading recent items:", e);
        }
    }

    // ========== FORMATTERS ==========
    formatNumber(value, decimals = 0) {
        if (value === null || value === undefined) return "0";
        return Number(value).toLocaleString('fr-FR', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }

    formatDate(dateStr) {
        if (!dateStr) return "-";
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR');
    }

    getStateLabel(state) {
        const labels = {
            'draft': 'Brouillon',
            'confirmed': 'Confirmé',
            'in_progress': 'En cours',
            'done': 'Terminé',
            'cancelled': 'Annulé',
            'lots_generated': 'Lots générés',
            'ready_validation': 'À valider',
            'ready': 'Prêt',
            'potted': 'Empoté',
            'in_production': 'En production'
        };
        return labels[state] || state;
    }

    getStateClass(state) {
        const classes = {
            'draft': 'bg-secondary',
            'confirmed': 'bg-primary',
            'in_progress': 'bg-info',
            'done': 'bg-success',
            'cancelled': 'bg-danger',
            'lots_generated': 'bg-info',
            'ready_validation': 'bg-warning',
            'ready': 'bg-primary',
            'potted': 'bg-success',
            'in_production': 'bg-warning'
        };
        return classes[state] || 'bg-secondary';
    }

    getProductTypeLabel(type) {
        const labels = {
            'masse': 'Masse de cacao',
            'beurre': 'Beurre de cacao',
            'poudre': 'Poudre de cacao',
            'tourteau': 'Tourteau de cacao'
        };
        return labels[type] || type;
    }

    // ========== NAVIGATION ==========
    viewTransitOrders() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Ordres de Transit",
            res_model: "potting.transit.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    viewLots() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Lots",
            res_model: "potting.lot",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    viewOT(otId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "potting.transit.order",
            res_id: otId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    viewLot(lotId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "potting.lot",
            res_id: lotId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("potting_user_dashboard", PottingUserDashboard);
