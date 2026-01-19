/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Dashboard pour le profil Comptable
 * Focus sur les factures transitaires, les paiements et les formules
 */
export class PottingAccountantDashboard extends Component {
    static template = "potting_management.AccountantDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            // Campagne active
            currentCampaign: null,
            
            // Statistiques factures transitaires
            invoiceStats: {
                total: 0,
                draft: 0,
                submitted: 0,
                validated: 0,
                ready_payment: 0,
                paid: 0,
                rejected: 0,
            },
            
            // Montants factures
            invoiceAmounts: {
                total: 0,
                validated: 0,
                ready_payment: 0,
                paid: 0,
                pending: 0,
            },
            
            // Statistiques paiements transitaires
            paymentStats: {
                total: 0,
                pending: 0,
                validated: 0,
                executed: 0,
                rejected: 0,
            },
            
            // Montants paiements
            paymentAmounts: {
                total: 0,
                pending: 0,
                executed: 0,
            },
            
            // Statistiques formules (paiements producteurs)
            formulePaymentStats: {
                total_formules: 0,
                awaiting_payment: 0,
                partial_paid: 0,
                paid: 0,
                total_montant: 0,
                total_paye: 0,
                reste_a_payer: 0,
            },
            
            // Factures à valider
            invoicesToValidate: [],
            
            // Factures prêtes au paiement
            invoicesReadyPayment: [],
            
            // Paiements en attente
            pendingPayments: [],
            
            // Formules en attente de paiement
            formulesPendingPayment: [],
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
                ["name", "code"],
                { limit: 1 }
            );
            if (campaigns.length > 0) {
                this.state.currentCampaign = campaigns[0];
            }
        } catch (e) {
            console.log("Campaign model not available");
        }

        await this.loadInvoiceStats();
        await this.loadPaymentStats();
        await this.loadFormulePaymentStats();
        await this.loadPendingItems();
    }

    async loadInvoiceStats() {
        try {
            // Total des factures
            this.state.invoiceStats.total = await this.orm.searchCount(
                "potting.forwarding.agent.invoice", []
            );

            // Factures par état
            const states = ['draft', 'submitted', 'validated', 'ready_payment', 'paid', 'rejected'];
            for (const state of states) {
                this.state.invoiceStats[state] = await this.orm.searchCount(
                    "potting.forwarding.agent.invoice",
                    [['state', '=', state]]
                );
            }

            // Montants des factures
            const invoiceData = await this.orm.searchRead(
                "potting.forwarding.agent.invoice",
                [],
                ["amount_total", "state"]
            );
            
            this.state.invoiceAmounts.total = invoiceData.reduce(
                (sum, inv) => sum + (inv.amount_total || 0), 0
            );
            this.state.invoiceAmounts.validated = invoiceData
                .filter(inv => inv.state === 'validated')
                .reduce((sum, inv) => sum + (inv.amount_total || 0), 0);
            this.state.invoiceAmounts.ready_payment = invoiceData
                .filter(inv => inv.state === 'ready_payment')
                .reduce((sum, inv) => sum + (inv.amount_total || 0), 0);
            this.state.invoiceAmounts.paid = invoiceData
                .filter(inv => inv.state === 'paid')
                .reduce((sum, inv) => sum + (inv.amount_total || 0), 0);
            this.state.invoiceAmounts.pending = invoiceData
                .filter(inv => ['draft', 'submitted', 'validated', 'ready_payment'].includes(inv.state))
                .reduce((sum, inv) => sum + (inv.amount_total || 0), 0);
        } catch (e) {
            console.log("Error loading invoice stats:", e);
        }
    }

    async loadPaymentStats() {
        try {
            // Total des paiements
            this.state.paymentStats.total = await this.orm.searchCount(
                "potting.forwarding.agent.payment", []
            );

            // Paiements par état
            const states = ['pending', 'validated', 'executed', 'rejected'];
            for (const state of states) {
                this.state.paymentStats[state] = await this.orm.searchCount(
                    "potting.forwarding.agent.payment",
                    [['state', '=', state]]
                );
            }

            // Montants des paiements
            const paymentData = await this.orm.searchRead(
                "potting.forwarding.agent.payment",
                [],
                ["amount", "state"]
            );
            
            this.state.paymentAmounts.total = paymentData.reduce(
                (sum, p) => sum + (p.amount || 0), 0
            );
            this.state.paymentAmounts.pending = paymentData
                .filter(p => p.state === 'pending')
                .reduce((sum, p) => sum + (p.amount || 0), 0);
            this.state.paymentAmounts.executed = paymentData
                .filter(p => p.state === 'executed')
                .reduce((sum, p) => sum + (p.amount || 0), 0);
        } catch (e) {
            console.log("Error loading payment stats:", e);
        }
    }

    async loadFormulePaymentStats() {
        try {
            // Total des formules
            this.state.formulePaymentStats.total_formules = await this.orm.searchCount(
                "potting.formule", []
            );

            // Formules par état de paiement
            this.state.formulePaymentStats.awaiting_payment = await this.orm.searchCount(
                "potting.formule",
                [['state', 'in', ['draft', 'validated']]]
            );
            this.state.formulePaymentStats.partial_paid = await this.orm.searchCount(
                "potting.formule",
                [['state', '=', 'partial_paid']]
            );
            this.state.formulePaymentStats.paid = await this.orm.searchCount(
                "potting.formule",
                [['state', '=', 'paid']]
            );

            // Montants des formules
            const formuleData = await this.orm.searchRead(
                "potting.formule",
                [],
                ["montant_total", "montant_paye", "reste_a_payer"]
            );
            
            this.state.formulePaymentStats.total_montant = formuleData.reduce(
                (sum, f) => sum + (f.montant_total || 0), 0
            );
            this.state.formulePaymentStats.total_paye = formuleData.reduce(
                (sum, f) => sum + (f.montant_paye || 0), 0
            );
            this.state.formulePaymentStats.reste_a_payer = formuleData.reduce(
                (sum, f) => sum + (f.reste_a_payer || 0), 0
            );
        } catch (e) {
            console.log("Error loading formule payment stats:", e);
        }
    }

    async loadPendingItems() {
        try {
            // Factures à valider
            this.state.invoicesToValidate = await this.orm.searchRead(
                "potting.forwarding.agent.invoice",
                [['state', '=', 'submitted']],
                ["reference", "forwarding_agent_id", "amount_total", "create_date"],
                { limit: 5, order: "create_date desc" }
            );

            // Factures prêtes au paiement
            this.state.invoicesReadyPayment = await this.orm.searchRead(
                "potting.forwarding.agent.invoice",
                [['state', '=', 'ready_payment']],
                ["reference", "forwarding_agent_id", "amount_total", "date_validation"],
                { limit: 5, order: "date_validation desc" }
            );

            // Paiements en attente
            this.state.pendingPayments = await this.orm.searchRead(
                "potting.forwarding.agent.payment",
                [['state', '=', 'pending']],
                ["reference", "forwarding_agent_id", "amount", "payment_date"],
                { limit: 5, order: "payment_date asc" }
            );

            // Formules en attente de paiement
            this.state.formulesPendingPayment = await this.orm.searchRead(
                "potting.formule",
                [['state', 'in', ['draft', 'validated', 'partial_paid']]],
                ["reference", "ot_id", "montant_total", "reste_a_payer", "state"],
                { limit: 5, order: "create_date desc" }
            );
        } catch (e) {
            console.log("Error loading pending items:", e);
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

    formatCurrency(value) {
        if (value === null || value === undefined) return "0";
        return Number(value).toLocaleString('fr-FR', {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
    }

    formatDate(dateStr) {
        if (!dateStr) return "-";
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR');
    }

    getInvoiceStateClass(state) {
        const classes = {
            'draft': 'bg-secondary',
            'submitted': 'bg-info',
            'validated': 'bg-primary',
            'ready_payment': 'bg-warning',
            'paid': 'bg-success',
            'rejected': 'bg-danger'
        };
        return classes[state] || 'bg-secondary';
    }

    getPaymentStateClass(state) {
        const classes = {
            'pending': 'bg-warning',
            'validated': 'bg-primary',
            'executed': 'bg-success',
            'rejected': 'bg-danger'
        };
        return classes[state] || 'bg-secondary';
    }

    getFormuleStateClass(state) {
        const classes = {
            'draft': 'bg-secondary',
            'validated': 'bg-primary',
            'partial_paid': 'bg-warning',
            'paid': 'bg-success',
            'cancelled': 'bg-danger'
        };
        return classes[state] || 'bg-secondary';
    }

    getStateLabel(state) {
        const labels = {
            'draft': 'Brouillon',
            'submitted': 'Soumise',
            'validated': 'Validée',
            'ready_payment': 'Prête au paiement',
            'paid': 'Payée',
            'rejected': 'Rejetée',
            'pending': 'En attente',
            'executed': 'Exécuté',
            'partial_paid': 'Partiellement payée',
            'cancelled': 'Annulée'
        };
        return labels[state] || state;
    }

    // ========== NAVIGATION ACTIONS ==========
    openInvoiceList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Toutes les factures transitaires",
            res_model: "potting.forwarding.agent.invoice",
            view_mode: "list,form,kanban",
            views: [[false, "list"], [false, "form"], [false, "kanban"]],
            target: "current",
        });
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

    openInvoicesReadyPayment() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Factures prêtes au paiement",
            res_model: "potting.forwarding.agent.invoice",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', 'ready_payment']],
            target: "current",
        });
    }

    openInvoicesByState(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `Factures - ${this.getStateLabel(state)}`,
            res_model: "potting.forwarding.agent.invoice",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', state]],
            target: "current",
        });
    }

    openPaymentList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Paiements transitaires",
            res_model: "potting.forwarding.agent.payment",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openPendingPayments() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Paiements en attente",
            res_model: "potting.forwarding.agent.payment",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', 'pending']],
            target: "current",
        });
    }

    openPaymentsByState(state) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: `Paiements - ${this.getStateLabel(state)}`,
            res_model: "potting.forwarding.agent.payment",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', '=', state]],
            target: "current",
        });
    }

    openFormuleList() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Formules (FO)",
            res_model: "potting.formule",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    openFormulesPendingPayment() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Formules en attente de paiement",
            res_model: "potting.formule",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [['state', 'in', ['draft', 'validated', 'partial_paid']]],
            target: "current",
        });
    }

    openInvoice(invoiceId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "potting.forwarding.agent.invoice",
            res_id: invoiceId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openPayment(paymentId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "potting.forwarding.agent.payment",
            res_id: paymentId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openFormule(formuleId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "potting.formule",
            res_id: formuleId,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("potting_accountant_dashboard", PottingAccountantDashboard);
