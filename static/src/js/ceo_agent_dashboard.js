/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class PottingCeoAgentDashboard extends Component {
    static template = "potting_management.CeoAgentDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            // Current campaign
            currentCampaign: null,
            lots: {
                draft: 0,
                in_production: 0,
                ready: 0,
                potted: 0,
            },
            transitOrders: {
                in_progress: 0,
                ready_validation: 0,
            },
            // Tonnage stats
            productionStats: {
                totalProduced: 0,
                totalPotted: 0,
            },
            lotsInProduction: [],
            lotsReadyToPot: [],
            otToValidate: [],
            todayProductions: [],
            totalTodayTonnage: 0,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        // Load current campaign
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

        // Load lots counts
        const lotStates = ['draft', 'in_production', 'ready', 'potted'];
        for (const state of lotStates) {
            const count = await this.orm.searchCount("potting.lot", [['state', '=', state]]);
            this.state.lots[state] = count;
        }

        // Load production tonnage stats
        const allLots = await this.orm.searchRead(
            "potting.lot",
            [],
            ["current_tonnage", "state"]
        );
        this.state.productionStats.totalProduced = allLots.reduce(
            (sum, l) => sum + (l.current_tonnage || 0), 0
        );
        this.state.productionStats.totalPotted = allLots
            .filter(l => l.state === 'potted')
            .reduce((sum, l) => sum + (l.current_tonnage || 0), 0);

        // Load transit orders counts for validation
        this.state.transitOrders.in_progress = await this.orm.searchCount(
            "potting.transit.order", 
            [['state', '=', 'in_progress']]
        );
        this.state.transitOrders.ready_validation = await this.orm.searchCount(
            "potting.transit.order", 
            [['state', '=', 'ready_validation']]
        );

        // Load lots in production
        this.state.lotsInProduction = await this.orm.searchRead(
            "potting.lot",
            [['state', '=', 'in_production']],
            ["name", "transit_order_id", "product_type", "target_tonnage", "current_tonnage", "fill_percentage", "is_full"],
            { limit: 10, order: "fill_percentage desc" }
        );

        // Load lots ready to pot
        this.state.lotsReadyToPot = await this.orm.searchRead(
            "potting.lot",
            [['state', '=', 'ready']],
            ["name", "transit_order_id", "product_type", "current_tonnage", "container_id"],
            { limit: 10, order: "create_date desc" }
        );

        // Load OT to validate
        this.state.otToValidate = await this.orm.searchRead(
            "potting.transit.order",
            [['state', '=', 'ready_validation']],
            ["name", "consignee_id", "product_type", "tonnage", "lot_count", "potted_lot_count"],
            { limit: 10, order: "create_date desc" }
        );

        // Load today's productions
        const today = new Date().toISOString().split('T')[0];
        this.state.todayProductions = await this.orm.searchRead(
            "potting.production.line",
            [['date', '=', today]],
            ["lot_id", "tonnage", "batch_number", "shift", "operator_id"],
            { order: "create_date desc" }
        );

        this.state.totalTodayTonnage = this.state.todayProductions.reduce(
            (sum, p) => sum + p.tonnage, 0
        );
    }

    openLots(state) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Lots',
            res_model: 'potting.lot',
            views: [[false, 'kanban'], [false, 'list'], [false, 'form']],
            domain: state ? [['state', '=', state]] : [],
            context: {},
        });
    }

    openTransitOrders(state) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Ordres de Transit',
            res_model: 'potting.transit.order',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: state ? [['state', '=', state]] : [],
            context: {},
        });
    }

    openLot(lotId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Lot',
            res_model: 'potting.lot',
            views: [[false, 'form']],
            res_id: lotId,
        });
    }

    openTransitOrder(otId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Ordre de Transit',
            res_model: 'potting.transit.order',
            views: [[false, 'form']],
            res_id: otId,
        });
    }

    addProduction() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Nouvelle production',
            res_model: 'potting.production.line',
            views: [[false, 'form']],
            target: 'new',
        });
    }

    openSendReportWizard() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Envoyer un rapport',
            res_model: 'potting.send.report.wizard',
            views: [[false, 'form']],
            target: 'new',
        });
    }

    getStateLabel(state) {
        const labels = {
            'draft': 'Brouillon',
            'in_production': 'En production',
            'ready': 'Prêt pour empotage',
            'potted': 'Empoté',
            'in_progress': 'En cours',
            'ready_validation': 'Prêt validation',
        };
        return labels[state] || state;
    }

    getStateBadgeClass(state) {
        const classes = {
            'draft': 'bg-secondary',
            'in_production': 'bg-warning',
            'ready': 'bg-info',
            'potted': 'bg-success',
            'in_progress': 'bg-warning',
            'ready_validation': 'bg-primary',
        };
        return classes[state] || 'bg-secondary';
    }

    getProductTypeLabel(type) {
        const labels = {
            'cocoa_mass': 'Masse',
            'cocoa_butter': 'Beurre',
            'cocoa_cake': 'Cake',
            'cocoa_powder': 'Poudre'
        };
        return labels[type] || type;
    }

    getShiftLabel(shift) {
        const labels = {
            'morning': 'Matin',
            'afternoon': 'Après-midi',
            'night': 'Nuit'
        };
        return labels[shift] || shift || '-';
    }

    formatNumber(num, decimals = 2) {
        if (typeof num !== 'number') return '0.00';
        return num.toLocaleString('fr-FR', { 
            minimumFractionDigits: decimals, 
            maximumFractionDigits: decimals 
        });
    }

    openCampaigns() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Campagnes',
            res_model: 'potting.campaign',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: [],
            context: {},
        });
    }
}

registry.category("actions").add("potting_ceo_agent_dashboard", PottingCeoAgentDashboard);
