/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Dashboard Finances - Factures, Paiements, Taxes
 * Simplifié et actionnable
 */
export class PottingFinancesDashboard extends Component {
    static template = "potting_management.FinancesDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            // Montants résumés
            amounts: {
                total_invoices: 0,
                pending: 0,
                paid: 0,
            },
            
            // Factures par état (nombres simples)
            invoices: {
                draft: 0,
                to_validate: 0,
                ready_payment: 0,
                paid: 0,
                rejected: 0,
                total: 0,
            },
            
            // Paiements
            payments: {
                count: 0,
                pending: 0,
                processing: 0,
                completed: 0,
                pending_amount: 0,
            },
            
            // Taxes & Paiements
            taxes: {
                avant_vente_paid: 0,  // Formules payées (producteurs)
                dus_paid: 0,          // OT avec DUS payé
                total_amount: 0,
                waiting_dus: 0,       // OT vendus en attente DUS
            },
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        try {
            await Promise.all([
                this.loadAmounts(),
                this.loadInvoiceStats(),
                this.loadPaymentStats(),
                this.loadTaxStats(),
            ]);
        } catch (e) {
            console.error("Erreur chargement finances:", e);
        }
    }

    async loadAmounts() {
        try {
            // Utiliser potting.forwarding.agent.invoice (factures transitaires)
            const invoices = await this.orm.searchRead(
                "potting.forwarding.agent.invoice",
                [['state', 'not in', ['cancelled', 'rejected']]],
                ["total_amount", "state"]
            );
            
            this.state.amounts.total_invoices = invoices.reduce((sum, i) => sum + (i.total_amount || 0), 0);
            
            const paidInvoices = invoices.filter(i => i.state === 'paid');
            this.state.amounts.paid = paidInvoices.reduce((sum, i) => sum + (i.total_amount || 0), 0);
            
            this.state.amounts.pending = this.state.amounts.total_invoices - this.state.amounts.paid;
        } catch (e) {
            console.log("Erreur montants:", e);
        }
    }

    async loadInvoiceStats() {
        try {
            // Factures transitaires par état
            this.state.invoices.draft = await this.orm.searchCount(
                "potting.forwarding.agent.invoice",
                [['state', '=', 'draft']]
            );
            
            this.state.invoices.to_validate = await this.orm.searchCount(
                "potting.forwarding.agent.invoice",
                [['state', '=', 'submitted']]
            );
            
            this.state.invoices.ready_payment = await this.orm.searchCount(
                "potting.forwarding.agent.invoice",
                [['state', '=', 'validated']]
            );
            
            this.state.invoices.paid = await this.orm.searchCount(
                "potting.forwarding.agent.invoice",
                [['state', '=', 'paid']]
            );
            
            this.state.invoices.rejected = await this.orm.searchCount(
                "potting.forwarding.agent.invoice",
                [['state', '=', 'rejected']]
            );
            
            this.state.invoices.total = 
                this.state.invoices.draft + 
                this.state.invoices.to_validate + 
                this.state.invoices.ready_payment + 
                this.state.invoices.paid +
                this.state.invoices.rejected;
        } catch (e) {
            console.log("Erreur stats factures:", e);
        }
    }

    async loadPaymentStats() {
        try {
            // Paiements ce mois
            const firstDay = new Date();
            firstDay.setDate(1);
            const firstDayStr = firstDay.toISOString().split('T')[0];
            
            this.state.payments.count = await this.orm.searchCount(
                "potting.forwarding.agent.payment",
                [['payment_date', '>=', firstDayStr]]
            );
            
            // États des paiements
            this.state.payments.pending = await this.orm.searchCount(
                "potting.forwarding.agent.payment",
                [['state', '=', 'draft']]
            );
            
            this.state.payments.processing = await this.orm.searchCount(
                "potting.forwarding.agent.payment",
                [['state', '=', 'in_progress']]
            );
            
            this.state.payments.completed = await this.orm.searchCount(
                "potting.forwarding.agent.payment",
                [['state', '=', 'done']]
            );
            
            // Montant en attente
            const pendingPayments = await this.orm.searchRead(
                "potting.forwarding.agent.payment",
                [['state', 'in', ['draft', 'in_progress']]],
                ["amount"]
            );
            this.state.payments.pending_amount = pendingPayments.reduce((sum, p) => sum + (p.amount || 0), 0);
        } catch (e) {
            console.log("Erreur stats paiements:", e);
        }
    }

    async loadTaxStats() {
        try {
            // Formules payées (producteurs)
            this.state.taxes.avant_vente_paid = await this.orm.searchCount(
                "potting.formule",
                [['active', '=', true], ['avant_vente_paye', '=', true]]
            );
            
            // OT avec DUS payé
            this.state.taxes.dus_paid = await this.orm.searchCount(
                "potting.transit.order",
                [['dus_paid', '=', true]]
            );
            
            // OT vendus en attente de paiement DUS
            this.state.taxes.waiting_dus = await this.orm.searchCount(
                "potting.transit.order",
                [['state', '=', 'sold'], ['dus_paid', '=', false]]
            );
            
            // Total taxes (somme des montants de taxes prélevées)
            const formules = await this.orm.searchRead(
                "potting.formule",
                [['active', '=', true]],
                ["total_taxes_prelevees"]
            );
            this.state.taxes.total_amount = formules.reduce((sum, f) => sum + (f.total_taxes_prelevees || 0), 0);
        } catch (e) {
            console.log("Erreur stats taxes:", e);
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

    // ========== ACTIONS ==========
    async refresh() {
        await this.loadData();
        this.notification.add("Données actualisées", { type: "success" });
    }

    openInvoicesToValidate() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Factures à valider",
            res_model: "potting.forwarding.agent.invoice",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', 'submitted']],
            target: "current",
        });
    }

    openInvoicesReady() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Factures prêtes au paiement",
            res_model: "potting.forwarding.agent.invoice",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', 'validated']],
            target: "current",
        });
    }

    openAllInvoices() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Factures Transitaires",
            res_model: "potting.forwarding.agent.invoice",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openInvoicesByState(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `Factures - ${state}`,
            res_model: "potting.forwarding.agent.invoice",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', state]],
            target: "current",
        });
    }

    openPayments() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Paiements",
            res_model: "potting.forwarding.agent.payment",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openFormules() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Formules",
            res_model: "potting.formule",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("potting_finances_dashboard", PottingFinancesDashboard);
