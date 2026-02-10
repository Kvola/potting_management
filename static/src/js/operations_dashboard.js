/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Dashboard Opérations - Production, OT, Lots
 * Unifie: OT Manager, CEO Agent, Shipping dashboards
 */
export class PottingOperationsDashboard extends Component {
    static template = "potting_management.OperationsDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            // Production
            production: {
                total: 0,
                potted: 0,
                today: 0,
            },
            
            // OT par état (nombres simples pour template)
            ot: {
                draft: 0,
                confirmed: 0,
                lots_generated: 0,
                in_progress: 0,
                ready_validation: 0,
                done: 0,
            },
            
            // Pourcentages OT pour barre de progression
            ot_percent: {
                draft: 0,
                confirmed: 0,
                lots_generated: 0,
                in_progress: 0,
                done: 0,
            },
            
            // Lots par état
            lots: {
                draft: 0,
                in_production: 0,
                produced: 0,
                potted: 0,
            },
            
            // Formules
            formules: {
                total: 0,
                paid: 0,
                unpaid: 0,
            },
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        try {
            await Promise.all([
                this.loadProduction(),
                this.loadOTStats(),
                this.loadLotsStats(),
                this.loadFormules(),
            ]);
        } catch (e) {
            console.error("Erreur chargement opérations:", e);
        }
    }

    async loadProduction() {
        try {
            // Tonnage total tous lots
            const allLots = await this.orm.searchRead(
                "potting.lot", [], ["current_tonnage", "state"]
            );
            this.state.production.total = allLots.reduce((sum, l) => sum + (l.current_tonnage || 0), 0);
            
            // Tonnage empoté
            this.state.production.potted = allLots
                .filter(l => l.state === 'potted')
                .reduce((sum, l) => sum + (l.current_tonnage || 0), 0);
            
            // Production du jour (tonnage ajouté aujourd'hui)
            const today = new Date().toISOString().split('T')[0];
            const todayLots = await this.orm.searchRead(
                "potting.lot",
                [['write_date', '>=', today]],
                ["current_tonnage"]
            );
            this.state.production.today = todayLots.reduce((sum, l) => sum + (l.current_tonnage || 0), 0);
        } catch (e) {
            console.log("Erreur production:", e);
        }
    }

    async loadOTStats() {
        try {
            const states = ['draft', 'confirmed', 'lots_generated', 'in_progress', 'ready_validation', 'done'];
            let total = 0;
            
            for (const state of states) {
                const count = await this.orm.searchCount(
                    "potting.transit.order",
                    [['state', '=', state]]
                );
                this.state.ot[state] = count;
                total += count;
            }
            
            // Calculer pourcentages
            if (total > 0) {
                for (const state of states) {
                    this.state.ot_percent[state] = Math.round((this.state.ot[state] / total) * 100);
                }
            }
        } catch (e) {
            console.log("Erreur stats OT:", e);
        }
    }

    async loadLotsStats() {
        try {
            this.state.lots.draft = await this.orm.searchCount(
                "potting.lot", [['state', '=', 'draft']]
            );
            this.state.lots.in_production = await this.orm.searchCount(
                "potting.lot", [['state', '=', 'in_production']]
            );
            this.state.lots.produced = await this.orm.searchCount(
                "potting.lot", [['state', '=', 'produced']]
            );
            this.state.lots.potted = await this.orm.searchCount(
                "potting.lot", [['state', '=', 'potted']]
            );
        } catch (e) {
            console.log("Erreur stats lots:", e);
        }
    }

    async loadFormules() {
        try {
            this.state.formules.total = await this.orm.searchCount(
                "potting.formule", [['active', '=', true]]
            );
            
            this.state.formules.paid = await this.orm.searchCount(
                "potting.formule", [['active', '=', true], ['state', '=', 'paid']]
            );
            
            this.state.formules.unpaid = await this.orm.searchCount(
                "potting.formule", [['active', '=', true], ['state', 'in', ['draft', 'validated']]]
            );
        } catch (e) {
            console.log("Erreur formules:", e);
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

    // ========== ACTIONS ==========
    async refresh() {
        await this.loadData();
        this.notification.add("Données actualisées", { type: "success" });
    }

    addQuickProduction() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Production rapide",
            res_model: "potting.quick.production.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
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

    createDeliveryNote() {
        // Ouvrir le wizard de livraison rapide pour sélectionner un OT et créer un BL
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Créer Bon de Livraison",
            res_model: "potting.quick.delivery.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        });
    }

    openAllOT() {
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
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `OT - ${state}`,
            res_model: "potting.transit.order",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', state]],
            target: "current",
        });
    }

    openAllLots() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Lots",
            res_model: "potting.lot",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openLots(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `Lots - ${state}`,
            res_model: "potting.lot",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', state]],
            target: "current",
        });
    }

    openAllFormules() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Formules",
            res_model: "potting.formule",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openFormulesPaid() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Formules payées",
            res_model: "potting.formule",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', 'paid'], ['active', '=', true]],
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
}

registry.category("actions").add("potting_operations_dashboard", PottingOperationsDashboard);
