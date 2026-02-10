/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Dashboard Principal Unifié - Vue d'ensemble intelligente
 * Simple, clair, actionnable
 */
export class PottingMainDashboard extends Component {
    static template = "potting_management.MainDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            // Campagne active
            campaign: null,
            
            // Alertes
            alerts: {
                total: 0,
                ot_to_validate: 0,
                invoices_pending: 0,
                lots_production: 0,
                formules_unpaid: 0,
            },
            
            // KPIs principaux
            kpis: {
                contracts: 0,
                transit_orders: 0,
                tonnage_shipped: 0,
                total_amount: 0,
            },
            
            // Progression
            progress: {
                percentage: 0,
                total: 0,
                used: 0,
                remaining: 0,
            },
            
            // États OT
            ot_states: {
                draft: 0,
                confirmed: 0,
                in_progress: 0,
                ready_validation: 0,
                done: 0,
            },
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        try {
            await Promise.all([
                this.loadCampaign(),
                this.loadAlerts(),
                this.loadKPIs(),
                this.loadProgress(),
                this.loadOTStates(),
            ]);
        } catch (e) {
            console.error("Erreur chargement dashboard:", e);
        }
    }

    async loadCampaign() {
        try {
            const campaigns = await this.orm.searchRead(
                "potting.campaign",
                [['state', '=', 'active']],
                ["name", "code"],
                { limit: 1 }
            );
            
            if (campaigns.length > 0) {
                const campaign = campaigns[0];
                // Compter OT de la campagne
                const otCount = await this.orm.searchCount(
                    "potting.transit.order",
                    [['campaign_id', '=', campaign.id], ['state', 'not in', ['cancelled']]]
                );
                // Tonnage de la campagne
                const lots = await this.orm.searchRead(
                    "potting.lot",
                    [['campaign_id', '=', campaign.id], ['state', '=', 'potted']],
                    ["current_tonnage"]
                );
                const tonnage = lots.reduce((sum, l) => sum + (l.current_tonnage || 0), 0);
                
                this.state.campaign = {
                    ...campaign,
                    ot_count: otCount,
                    tonnage: tonnage,
                };
            }
        } catch (e) {
            console.log("Campagne non disponible:", e);
        }
    }

    async loadAlerts() {
        try {
            // OT à valider
            this.state.alerts.ot_to_validate = await this.orm.searchCount(
                "potting.transit.order",
                [['state', '=', 'ready_validation']]
            );
            
            // Factures en attente
            try {
                this.state.alerts.invoices_pending = await this.orm.searchCount(
                    "potting.forwarding.agent.invoice",
                    [['state', '=', 'submitted']]
                );
            } catch (e) {
                this.state.alerts.invoices_pending = 0;
            }
            
            // Lots en production
            this.state.alerts.lots_production = await this.orm.searchCount(
                "potting.lot",
                [['state', '=', 'in_production']]
            );
            
            // Formules impayées
            try {
                this.state.alerts.formules_unpaid = await this.orm.searchCount(
                    "potting.formule",
                    [['state', 'in', ['draft', 'validated']], ['active', '=', true]]
                );
            } catch (e) {
                this.state.alerts.formules_unpaid = 0;
            }
            
            this.state.alerts.total = 
                this.state.alerts.ot_to_validate + 
                this.state.alerts.invoices_pending + 
                this.state.alerts.lots_production +
                this.state.alerts.formules_unpaid;
        } catch (e) {
            console.log("Erreur alertes:", e);
        }
    }

    async loadKPIs() {
        try {
            // Contrats actifs
            this.state.kpis.contracts = await this.orm.searchCount(
                "potting.customer.order",
                [['state', '=', 'validated']]
            );
            
            // OT non annulés
            this.state.kpis.transit_orders = await this.orm.searchCount(
                "potting.transit.order",
                [['state', 'not in', ['cancelled']]]
            );
            
            // Tonnage expédié (lots empotés)
            const lots = await this.orm.searchRead(
                "potting.lot",
                [['state', '=', 'potted']],
                ["current_tonnage"]
            );
            this.state.kpis.tonnage_shipped = lots.reduce((sum, l) => sum + (l.current_tonnage || 0), 0);
            
            // Montant total (contrats validés)
            const contracts = await this.orm.searchRead(
                "potting.customer.order",
                [['state', '=', 'validated']],
                ["total_amount"]
            );
            this.state.kpis.total_amount = contracts.reduce((sum, c) => sum + (c.total_amount || 0), 0);
        } catch (e) {
            console.log("Erreur KPIs:", e);
        }
    }

    async loadProgress() {
        try {
            // Tonnage total contracté
            const contracts = await this.orm.searchRead(
                "potting.customer.order",
                [['state', '=', 'validated']],
                ["tonnage"]
            );
            const totalContracted = contracts.reduce((sum, c) => sum + (c.tonnage || 0), 0);
            
            // Tonnage utilisé dans les OT
            const ots = await this.orm.searchRead(
                "potting.transit.order",
                [['state', 'not in', ['cancelled', 'draft']]],
                ["total_tonnage"]
            );
            const usedTonnage = ots.reduce((sum, ot) => sum + (ot.total_tonnage || 0), 0);
            
            this.state.progress.total = totalContracted;
            this.state.progress.used = usedTonnage;
            this.state.progress.remaining = Math.max(0, totalContracted - usedTonnage);
            this.state.progress.percentage = totalContracted > 0 
                ? (usedTonnage / totalContracted) * 100 
                : 0;
        } catch (e) {
            console.log("Erreur progression:", e);
        }
    }

    async loadOTStates() {
        try {
            const states = ['draft', 'confirmed', 'in_progress', 'ready_validation', 'done'];
            for (const state of states) {
                let domain = [['state', '=', state]];
                if (state === 'draft') {
                    domain = [['state', 'in', ['draft', 'lots_generated']]];
                }
                this.state.ot_states[state] = await this.orm.searchCount(
                    "potting.transit.order", domain
                );
            }
        } catch (e) {
            console.log("Erreur états OT:", e);
        }
    }

    // ========== FORMATTERS ==========
    formatNumber(value, decimals = 0) {
        if (value === null || value === undefined || isNaN(value)) return "0";
        return Number(value).toLocaleString('fr-FR', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        });
    }

    formatCurrency(value) {
        if (value === null || value === undefined || isNaN(value)) return "0";
        if (value >= 1000000000) {
            return (value / 1000000000).toFixed(1) + " Mrd";
        }
        if (value >= 1000000) {
            return (value / 1000000).toFixed(1) + " M";
        }
        if (value >= 1000) {
            return Math.round(value / 1000) + " K";
        }
        return this.formatNumber(value);
    }

    // ========== ACTIONS NAVIGATION ==========
    async refresh() {
        await this.loadData();
        this.notification.add("Données actualisées", { type: "success" });
    }

    openOTToValidate() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "OT à valider",
            res_model: "potting.transit.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', 'ready_validation']],
            target: "current",
        });
    }

    openInvoicesPending() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Factures en attente",
            res_model: "potting.forwarding.agent.invoice",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', 'submitted']],
            target: "current",
        });
    }

    openLotsProduction() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Lots en production",
            res_model: "potting.lot",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', 'in_production']],
            target: "current",
        });
    }

    openFormulesUnpaid() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Formules impayées",
            res_model: "potting.formule",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', 'in', ['draft', 'validated']], ['active', '=', true]],
            target: "current",
        });
    }

    openContracts() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Contrats",
            res_model: "potting.customer.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openTransitOrders() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Ordres de Transit",
            res_model: "potting.transit.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openOTs(state) {
        let domain = [['state', '=', state]];
        if (state === 'draft') {
            domain = [['state', 'in', ['draft', 'lots_generated']]];
        }
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `OT - ${state}`,
            res_model: "potting.transit.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain,
            target: "current",
        });
    }

    createContract() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Nouveau contrat",
            res_model: "potting.customer.order",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    createOT() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Nouvel OT",
            res_model: "potting.transit.order",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    addProduction() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Production rapide",
            res_model: "potting.quick.production.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        });
    }

    openReports() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Rapport quotidien",
            res_model: "potting.daily.report.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        });
    }
}

registry.category("actions").add("potting_main_dashboard", PottingMainDashboard);
