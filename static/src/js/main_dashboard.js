/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Dashboard Unifié Intelligent - Adaptatif selon le rôle utilisateur
 * 
 * Rôles détectés:
 *  - Commercial: Contrats, progression tonnage
 *  - Agent CCC: CV, tonnage autorisé/utilisé
 *  - Gestionnaire OT: Pipeline OT, allocations
 *  - Gestionnaire Formules: Formules, paiements producteurs
 *  - Shipping: Lots, conteneurs, BL, production
 *  - Comptable: Factures, paiements, taxes
 *  - Agent Exportation: Validation OT, rapports
 *  - Manager: Vue complète
 */
export class PottingMainDashboard extends Component {
    static template = "potting_management.MainDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.user = useService("user");

        this.state = useState({
            loading: true,
            darkMode: localStorage.getItem('potting_dashboard_dark_mode') === '1',

            // Rôles utilisateur
            roles: {
                is_commercial: false,
                is_agent_ccc: false,
                is_ot_manager: false,
                is_formule_manager: false,
                is_accountant: false,
                is_shipping: false,
                is_ceo_agent: false,
                is_manager: false,
            },

            // Campagne active
            campaign: null,

            // KPIs globaux par produit
            products: {
                cocoa_mass: { label: "Masse", ot_count: 0, tonnage: 0, contracts: 0, icon: "fa-cube" },
                cocoa_butter: { label: "Beurre", ot_count: 0, tonnage: 0, contracts: 0, icon: "fa-tint" },
                cocoa_cake: { label: "Cake", ot_count: 0, tonnage: 0, contracts: 0, icon: "fa-circle" },
                cocoa_powder: { label: "Poudre", ot_count: 0, tonnage: 0, contracts: 0, icon: "fa-dot-circle-o" },
            },
            totals: {
                contracts: 0,
                ot: 0,
                tonnage_shipped: 0,
                total_amount: 0,
                cv_active: 0,
                formules: 0,
            },

            // Alertes par rôle (dynamiques)
            alerts: [],

            // Pipeline OT
            ot_pipeline: {
                draft: 0,
                formule_linked: 0,
                taxes_paid: 0,
                lots_generated: 0,
                in_progress: 0,
                ready_validation: 0,
                sold: 0,
                sent_to_customer: 0,
                dus_paid: 0,
                done: 0,
            },

            // Progression tonnage (contrats)
            progress: {
                contracted: 0,
                allocated_ot: 0,
                produced: 0,
                potted: 0,
                delivered: 0,
            },

            // Lots
            lots: {
                draft: 0,
                in_production: 0,
                ready: 0,
                potted: 0,
            },

            // Conteneurs
            containers: {
                available: 0,
                loading: 0,
                loaded: 0,
                shipped: 0,
            },

            // CV
            cv: {
                active: 0,
                tonnage_autorise: 0,
                tonnage_utilise: 0,
                expiring_soon: 0,
            },

            // Formules
            formules: {
                draft: 0,
                validated: 0,
                paid: 0,
                total_taxes: 0,
                unpaid_amount: 0,
            },

            // Finances
            finances: {
                invoices_draft: 0,
                invoices_to_validate: 0,
                invoices_ready: 0,
                invoices_paid: 0,
                invoices_rejected: 0,
                total_invoiced: 0,
                total_paid: 0,
                ot_waiting_taxes: 0,
                ot_waiting_dus: 0,
                payments_pending_amount: 0,
            },

            // BL
            delivery_notes: {
                draft: 0,
                confirmed: 0,
                delivered: 0,
            },

            // Production du jour
            production_today: 0,
        });

        onWillStart(async () => {
            await this.detectRoles();
            await this.loadData();
            this.state.loading = false;
        });
    }

    // ========== MODE SOMBRE ==========
    toggleDarkMode() {
        this.state.darkMode = !this.state.darkMode;
        localStorage.setItem('potting_dashboard_dark_mode', this.state.darkMode ? '1' : '0');
    }

    // ========== DÉTECTION DES RÔLES ==========
    async detectRoles() {
        const groupChecks = [
            ["potting_management.group_potting_commercial", "is_commercial"],
            ["potting_management.group_potting_agent_ccc", "is_agent_ccc"],
            ["potting_management.group_potting_ot_manager", "is_ot_manager"],
            ["potting_management.group_potting_formule_manager", "is_formule_manager"],
            ["potting_management.group_potting_accountant", "is_accountant"],
            ["potting_management.group_potting_shipping", "is_shipping"],
            ["potting_management.group_potting_ceo_agent", "is_ceo_agent"],
            ["potting_management.group_potting_manager", "is_manager"],
        ];

        const results = await Promise.all(
            groupChecks.map(([group]) => this.user.hasGroup(group))
        );

        groupChecks.forEach(([, key], i) => {
            this.state.roles[key] = results[i];
        });
    }

    // ========== CHARGEMENT DES DONNÉES ==========
    async loadData() {
        const tasks = [
            this.loadCampaign(),
            this.loadProductBreakdown(),
            this.loadProgress(),
        ];

        // Charger selon les rôles
        const r = this.state.roles;
        if (r.is_ot_manager || r.is_ceo_agent || r.is_manager) {
            tasks.push(this.loadOTPipeline());
        }
        if (r.is_shipping || r.is_ceo_agent || r.is_manager) {
            tasks.push(this.loadLotsStats());
            tasks.push(this.loadProductionToday());
        }
        if (r.is_shipping || r.is_manager) {
            tasks.push(this.loadContainerStats());
            tasks.push(this.loadDeliveryNotesStats());
        }
        if (r.is_agent_ccc || r.is_manager) {
            tasks.push(this.loadCVStats());
        }
        if (r.is_formule_manager || r.is_accountant || r.is_manager) {
            tasks.push(this.loadFormuleStats());
        }
        if (r.is_accountant || r.is_manager) {
            tasks.push(this.loadFinanceStats());
        }

        try {
            await Promise.all(tasks);
            this.buildAlerts();
        } catch (e) {
            console.error("Erreur chargement dashboard:", e);
        }
    }

    async loadCampaign() {
        try {
            const campaigns = await this.orm.searchRead(
                "potting.campaign",
                [["state", "=", "active"]],
                ["name", "code", "date_start", "date_end", "transit_order_count", "total_tonnage", "total_amount", "customer_order_count"],
                { limit: 1 }
            );
            if (campaigns.length > 0) {
                this.state.campaign = campaigns[0];
            }
        } catch (e) {
            console.log("Campagne non disponible:", e);
        }
    }

    async loadProductBreakdown() {
        try {
            const campaignDomain = this.state.campaign
                ? [["campaign_id", "=", this.state.campaign.id]]
                : [];

            // OT par produit (non annulés)
            const ots = await this.orm.searchRead(
                "potting.transit.order",
                [...campaignDomain, ["state", "not in", ["cancelled"]]],
                ["product_type", "tonnage", "current_tonnage", "total_amount", "state"]
            );

            let totalOT = 0;
            let totalTonnage = 0;
            let totalAmount = 0;
            const productStats = {};

            for (const ot of ots) {
                const pt = ot.product_type;
                if (!productStats[pt]) {
                    productStats[pt] = { ot_count: 0, tonnage: 0 };
                }
                productStats[pt].ot_count++;
                productStats[pt].tonnage += ot.current_tonnage || 0;
                totalOT++;
                totalTonnage += ot.current_tonnage || 0;
                totalAmount += ot.total_amount || 0;
            }

            for (const [key, stats] of Object.entries(productStats)) {
                if (this.state.products[key]) {
                    this.state.products[key].ot_count = stats.ot_count;
                    this.state.products[key].tonnage = stats.tonnage;
                }
            }

            // Contrats par produit
            const contracts = await this.orm.searchRead(
                "potting.customer.order",
                [["state", "in", ["confirmed", "in_progress", "done"]]],
                ["product_type", "contract_tonnage"]
            );

            let totalContracts = 0;
            for (const c of contracts) {
                if (this.state.products[c.product_type]) {
                    this.state.products[c.product_type].contracts++;
                }
                totalContracts++;
            }

            this.state.totals.contracts = totalContracts;
            this.state.totals.ot = totalOT;
            this.state.totals.tonnage_shipped = totalTonnage;
            this.state.totals.total_amount = totalAmount;
        } catch (e) {
            console.log("Erreur product breakdown:", e);
        }
    }

    async loadProgress() {
        try {
            // Tonnage contracté
            const contracts = await this.orm.searchRead(
                "potting.customer.order",
                [["state", "in", ["confirmed", "in_progress"]]],
                ["contract_tonnage"]
            );
            this.state.progress.contracted = contracts.reduce((s, c) => s + (c.contract_tonnage || 0), 0);

            const campaignDomain = this.state.campaign
                ? [["campaign_id", "=", this.state.campaign.id]]
                : [];

            // Tonnage alloué aux OT
            const ots = await this.orm.searchRead(
                "potting.transit.order",
                [...campaignDomain, ["state", "not in", ["cancelled", "draft"]]],
                ["tonnage"]
            );
            this.state.progress.allocated_ot = ots.reduce((s, o) => s + (o.tonnage || 0), 0);

            // Tonnage produit (lots en production ou plus)
            const lotsProduced = await this.orm.searchRead(
                "potting.lot",
                [...campaignDomain, ["state", "in", ["in_production", "ready", "potted"]]],
                ["current_tonnage"]
            );
            this.state.progress.produced = lotsProduced.reduce((s, l) => s + (l.current_tonnage || 0), 0);

            // Tonnage empoté
            const lotsPotted = await this.orm.searchRead(
                "potting.lot",
                [...campaignDomain, ["state", "=", "potted"]],
                ["current_tonnage"]
            );
            this.state.progress.potted = lotsPotted.reduce((s, l) => s + (l.current_tonnage || 0), 0);

            // Tonnage livré (BL livrés)
            const bls = await this.orm.searchRead(
                "potting.delivery.note",
                [["state", "=", "delivered"]],
                ["total_tonnage"]
            );
            this.state.progress.delivered = bls.reduce((s, b) => s + (b.total_tonnage || 0), 0);
        } catch (e) {
            console.log("Erreur progression:", e);
        }
    }

    async loadOTPipeline() {
        try {
            const campaignDomain = this.state.campaign
                ? [["campaign_id", "=", this.state.campaign.id]]
                : [];
            const states = Object.keys(this.state.ot_pipeline);

            const counts = await Promise.all(
                states.map((st) =>
                    this.orm.searchCount("potting.transit.order", [
                        ...campaignDomain,
                        ["state", "=", st],
                    ])
                )
            );
            states.forEach((st, i) => {
                this.state.ot_pipeline[st] = counts[i];
            });
        } catch (e) {
            console.log("Erreur pipeline OT:", e);
        }
    }

    async loadLotsStats() {
        try {
            const campaignDomain = this.state.campaign
                ? [["campaign_id", "=", this.state.campaign.id]]
                : [];
            const states = ["draft", "in_production", "ready", "potted"];
            const counts = await Promise.all(
                states.map((st) =>
                    this.orm.searchCount("potting.lot", [
                        ...campaignDomain,
                        ["state", "=", st],
                    ])
                )
            );
            states.forEach((st, i) => {
                this.state.lots[st] = counts[i];
            });
        } catch (e) {
            console.log("Erreur lots:", e);
        }
    }

    async loadProductionToday() {
        try {
            const today = new Date().toISOString().split("T")[0];
            const lines = await this.orm.searchRead(
                "potting.production.line",
                [["date", "=", today]],
                ["tonnage"]
            );
            this.state.production_today = lines.reduce((s, l) => s + (l.tonnage || 0), 0);
        } catch (e) {
            console.log("Erreur production today:", e);
        }
    }

    async loadContainerStats() {
        try {
            const states = ["available", "loading", "loaded", "shipped"];
            const counts = await Promise.all(
                states.map((st) =>
                    this.orm.searchCount("potting.container", [["state", "=", st]])
                )
            );
            states.forEach((st, i) => {
                this.state.containers[st] = counts[i];
            });
        } catch (e) {
            console.log("Erreur conteneurs:", e);
        }
    }

    async loadDeliveryNotesStats() {
        try {
            const states = ["draft", "confirmed", "delivered"];
            const counts = await Promise.all(
                states.map((st) =>
                    this.orm.searchCount("potting.delivery.note", [["state", "=", st]])
                )
            );
            states.forEach((st, i) => {
                this.state.delivery_notes[st] = counts[i];
            });
        } catch (e) {
            console.log("Erreur BL:", e);
        }
    }

    async loadCVStats() {
        try {
            const cvs = await this.orm.searchRead(
                "potting.confirmation.vente",
                [["state", "=", "active"]],
                ["tonnage_autorise", "tonnage_utilise", "tonnage_restant", "days_remaining"]
            );
            this.state.cv.active = cvs.length;
            this.state.cv.tonnage_autorise = cvs.reduce((s, c) => s + (c.tonnage_autorise || 0), 0);
            this.state.cv.tonnage_utilise = cvs.reduce((s, c) => s + (c.tonnage_utilise || 0), 0);
            this.state.cv.expiring_soon = cvs.filter((c) => c.days_remaining > 0 && c.days_remaining <= 30).length;
            this.state.totals.cv_active = cvs.length;
        } catch (e) {
            console.log("Erreur CV:", e);
        }
    }

    async loadFormuleStats() {
        try {
            const formules = await this.orm.searchRead(
                "potting.formule",
                [["active", "=", true], ["state", "!=", "cancelled"]],
                ["state", "total_taxes_prelevees", "reste_a_payer"]
            );
            for (const f of formules) {
                if (f.state === "draft") this.state.formules.draft++;
                else if (f.state === "validated") this.state.formules.validated++;
                else if (f.state === "paid") this.state.formules.paid++;
            }
            this.state.formules.total_taxes = formules.reduce(
                (s, f) => s + (f.total_taxes_prelevees || 0), 0
            );
            this.state.formules.unpaid_amount = formules.reduce(
                (s, f) => s + (f.reste_a_payer || 0), 0
            );
            this.state.totals.formules = formules.length;
        } catch (e) {
            console.log("Erreur formules:", e);
        }
    }

    async loadFinanceStats() {
        try {
            // Factures transitaires
            const invoices = await this.orm.searchRead(
                "potting.forwarding.agent.invoice",
                [],
                ["state", "amount_total"]
            );
            let totalInvoiced = 0;
            let totalPaid = 0;
            for (const inv of invoices) {
                if (inv.state === "draft") this.state.finances.invoices_draft++;
                else if (inv.state === "submitted") this.state.finances.invoices_to_validate++;
                else if (inv.state === "validated") this.state.finances.invoices_ready++;
                else if (inv.state === "paid") {
                    this.state.finances.invoices_paid++;
                    totalPaid += inv.amount_total || 0;
                }
                else if (inv.state === "rejected") this.state.finances.invoices_rejected++;
                if (inv.state !== "cancelled") {
                    totalInvoiced += inv.amount_total || 0;
                }
            }
            this.state.finances.total_invoiced = totalInvoiced;
            this.state.finances.total_paid = totalPaid;

            // OT en attente taxes / DUS
            const campaignDomain = this.state.campaign
                ? [["campaign_id", "=", this.state.campaign.id]]
                : [];

            this.state.finances.ot_waiting_taxes = await this.orm.searchCount(
                "potting.transit.order",
                [...campaignDomain, ["state", "=", "formule_linked"]]
            );
            this.state.finances.ot_waiting_dus = await this.orm.searchCount(
                "potting.transit.order",
                [...campaignDomain, ["state", "=", "sold"], ["dus_paid", "=", false]]
            );

            // Paiements en attente
            try {
                const pendingP = await this.orm.searchRead(
                    "potting.forwarding.agent.payment",
                    [["state", "in", ["draft", "in_progress"]]],
                    ["amount"]
                );
                this.state.finances.payments_pending_amount = pendingP.reduce(
                    (s, p) => s + (p.amount || 0), 0
                );
            } catch (e) {
                this.state.finances.payments_pending_amount = 0;
            }
        } catch (e) {
            console.log("Erreur finances:", e);
        }
    }

    // ========== ALERTES INTELLIGENTES ==========
    buildAlerts() {
        const alerts = [];
        const r = this.state.roles;

        // OT à valider (Agent Exportation / Manager)
        if ((r.is_ceo_agent || r.is_manager) && this.state.ot_pipeline.ready_validation > 0) {
            alerts.push({
                type: "warning", icon: "fa-gavel",
                count: this.state.ot_pipeline.ready_validation,
                label: "OT en attente de validation",
                action: "openOTsByState", params: "ready_validation",
            });
        }

        // Factures à valider (Comptable)
        if ((r.is_accountant || r.is_manager) && this.state.finances.invoices_to_validate > 0) {
            alerts.push({
                type: "info", icon: "fa-file-text",
                count: this.state.finances.invoices_to_validate,
                label: "Factures à valider",
                action: "openInvoicesToValidate", params: null,
            });
        }

        // OT en attente taxes (Comptable)
        if ((r.is_accountant || r.is_manager) && this.state.finances.ot_waiting_taxes > 0) {
            alerts.push({
                type: "warning", icon: "fa-university",
                count: this.state.finances.ot_waiting_taxes,
                label: "OT en attente taxes",
                action: "openOTsByState", params: "formule_linked",
            });
        }

        // OT en attente DUS (Comptable)
        if ((r.is_accountant || r.is_manager) && this.state.finances.ot_waiting_dus > 0) {
            alerts.push({
                type: "danger", icon: "fa-exclamation-circle",
                count: this.state.finances.ot_waiting_dus,
                label: "OT en attente DUS",
                action: "openOTWaitingDUS", params: null,
            });
        }

        // Formules à payer (Formule Manager / Comptable)
        if ((r.is_formule_manager || r.is_accountant || r.is_manager) && this.state.formules.validated > 0) {
            alerts.push({
                type: "danger", icon: "fa-money",
                count: this.state.formules.validated,
                label: "Formules à payer (producteurs)",
                action: "openFormulesToPay", params: null,
            });
        }

        // Lots en production (Shipping / CEO)
        if ((r.is_shipping || r.is_ceo_agent || r.is_manager) && this.state.lots.in_production > 0) {
            alerts.push({
                type: "primary", icon: "fa-industry",
                count: this.state.lots.in_production,
                label: "Lots en production",
                action: "openLotsByState", params: "in_production",
            });
        }

        // Lots prêts à empoter (Shipping)
        if ((r.is_shipping || r.is_manager) && this.state.lots.ready > 0) {
            alerts.push({
                type: "success", icon: "fa-archive",
                count: this.state.lots.ready,
                label: "Lots prêts à empoter",
                action: "openLotsByState", params: "ready",
            });
        }

        // CV expirant bientôt (Agent CCC)
        if ((r.is_agent_ccc || r.is_manager) && this.state.cv.expiring_soon > 0) {
            alerts.push({
                type: "warning", icon: "fa-clock-o",
                count: this.state.cv.expiring_soon,
                label: "CV expirant sous 30 jours",
                action: "openCVExpiring", params: null,
            });
        }

        // BL en brouillon (Shipping)
        if ((r.is_shipping || r.is_manager) && this.state.delivery_notes.draft > 0) {
            alerts.push({
                type: "secondary", icon: "fa-file-o",
                count: this.state.delivery_notes.draft,
                label: "BL en brouillon",
                action: "openDeliveryNotesByState", params: "draft",
            });
        }

        // Factures prêtes au paiement (Comptable)
        if ((r.is_accountant || r.is_manager) && this.state.finances.invoices_ready > 0) {
            alerts.push({
                type: "success", icon: "fa-check-circle",
                count: this.state.finances.invoices_ready,
                label: "Factures prêtes au paiement",
                action: "openInvoicesReady", params: null,
            });
        }

        this.state.alerts = alerts;
    }

    // ========== HELPERS VISIBILITÉ PAR RÔLE ==========
    get showCommercial() {
        return this.state.roles.is_commercial || this.state.roles.is_manager;
    }
    get showAgentCCC() {
        return this.state.roles.is_agent_ccc || this.state.roles.is_manager;
    }
    get showOTManager() {
        return this.state.roles.is_ot_manager || this.state.roles.is_ceo_agent || this.state.roles.is_manager;
    }
    get showFormuleManager() {
        return this.state.roles.is_formule_manager || this.state.roles.is_accountant || this.state.roles.is_manager;
    }
    get showShipping() {
        return this.state.roles.is_shipping || this.state.roles.is_ceo_agent || this.state.roles.is_manager;
    }
    get showAccountant() {
        return this.state.roles.is_accountant || this.state.roles.is_manager;
    }
    get showCEOAgent() {
        return this.state.roles.is_ceo_agent || this.state.roles.is_manager;
    }
    get showManager() {
        return this.state.roles.is_manager;
    }

    // ========== OT PIPELINE HELPERS ==========
    get otPipelineStages() {
        const p = this.state.ot_pipeline;
        return [
            { key: "draft", label: "Brouillon", count: p.draft, color: "secondary" },
            { key: "formule_linked", label: "FO liée", count: p.formule_linked, color: "info" },
            { key: "taxes_paid", label: "Taxes", count: p.taxes_paid, color: "primary" },
            { key: "lots_generated", label: "Lots", count: p.lots_generated, color: "primary" },
            { key: "in_progress", label: "En cours", count: p.in_progress, color: "warning" },
            { key: "ready_validation", label: "À valider", count: p.ready_validation, color: "danger" },
            { key: "sold", label: "Vendu", count: p.sold, color: "info" },
            { key: "dus_paid", label: "DUS", count: p.dus_paid, color: "primary" },
            { key: "done", label: "Terminé", count: p.done, color: "success" },
        ];
    }

    get otTotal() {
        return Object.values(this.state.ot_pipeline).reduce((s, v) => s + v, 0);
    }

    get progressPercentages() {
        const p = this.state.progress;
        const max = Math.max(p.contracted, 1);
        return {
            allocated: Math.min((p.allocated_ot / max) * 100, 100),
            produced: Math.min((p.produced / max) * 100, 100),
            potted: Math.min((p.potted / max) * 100, 100),
            delivered: Math.min((p.delivered / max) * 100, 100),
        };
    }

    get cvUsagePercent() {
        const cv = this.state.cv;
        if (cv.tonnage_autorise <= 0) return 0;
        return Math.min((cv.tonnage_utilise / cv.tonnage_autorise) * 100, 100);
    }

    // ========== FORMATTERS ==========
    formatNumber(value, decimals = 0) {
        if (value === null || value === undefined || isNaN(value)) return "0";
        return Number(value).toLocaleString("fr-FR", {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
        });
    }

    formatCurrency(value) {
        if (value === null || value === undefined || isNaN(value)) return "0";
        if (value >= 1000000000) return (value / 1000000000).toFixed(1) + " Mrd";
        if (value >= 1000000) return (value / 1000000).toFixed(1) + " M";
        if (value >= 1000) return Math.round(value / 1000) + " K";
        return this.formatNumber(value);
    }

    // ========== ACTIONS - NAVIGATION ==========
    async refresh() {
        this.state.loading = true;
        // Reset counters
        Object.keys(this.state.ot_pipeline).forEach(k => this.state.ot_pipeline[k] = 0);
        Object.keys(this.state.lots).forEach(k => this.state.lots[k] = 0);
        Object.keys(this.state.containers).forEach(k => this.state.containers[k] = 0);
        Object.keys(this.state.cv).forEach(k => this.state.cv[k] = 0);
        Object.keys(this.state.formules).forEach(k => this.state.formules[k] = 0);
        Object.keys(this.state.finances).forEach(k => this.state.finances[k] = 0);
        Object.keys(this.state.delivery_notes).forEach(k => this.state.delivery_notes[k] = 0);
        this.state.production_today = 0;
        await this.loadData();
        this.state.loading = false;
        this.notification.add("Données actualisées", { type: "success" });
    }

    handleAlertClick(alert) {
        if (alert.params !== null && alert.params !== undefined) {
            this[alert.action](alert.params);
        } else {
            this[alert.action]();
        }
    }

    // --- Contrats ---
    openContracts() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Contrats",
            res_model: "potting.customer.order", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "in", ["confirmed", "in_progress"]]], target: "current",
        });
    }
    createContract() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Nouveau contrat",
            res_model: "potting.customer.order", view_mode: "form",
            views: [[false, "form"]], target: "current",
        });
    }

    // --- OT ---
    openAllOT() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Ordres de Transit",
            res_model: "potting.transit.order", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: this.state.campaign ? [["campaign_id", "=", this.state.campaign.id]] : [],
            target: "current",
        });
    }
    openOTsByState(state) {
        const cd = this.state.campaign ? [["campaign_id", "=", this.state.campaign.id]] : [];
        this.action.doAction({
            type: "ir.actions.act_window", name: `OT - ${state}`,
            res_model: "potting.transit.order", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [...cd, ["state", "=", state]], target: "current",
        });
    }
    openOTWaitingDUS() {
        const cd = this.state.campaign ? [["campaign_id", "=", this.state.campaign.id]] : [];
        this.action.doAction({
            type: "ir.actions.act_window", name: "OT en attente DUS",
            res_model: "potting.transit.order", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [...cd, ["state", "=", "sold"], ["dus_paid", "=", false]], target: "current",
        });
    }
    createOT() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Nouvel OT",
            res_model: "potting.transit.order", view_mode: "form",
            views: [[false, "form"]], target: "current",
        });
    }

    // --- Lots ---
    openAllLots() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Lots",
            res_model: "potting.lot", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]], target: "current",
        });
    }
    openLotsByState(state) {
        this.action.doAction({
            type: "ir.actions.act_window", name: `Lots - ${state}`,
            res_model: "potting.lot", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", state]], target: "current",
        });
    }

    // --- Conteneurs ---
    openContainers() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Conteneurs",
            res_model: "potting.container", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]], target: "current",
        });
    }
    openContainersByState(state) {
        this.action.doAction({
            type: "ir.actions.act_window", name: `Conteneurs - ${state}`,
            res_model: "potting.container", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", state]], target: "current",
        });
    }

    // --- CV ---
    openCVActive() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "CV Actives",
            res_model: "potting.confirmation.vente", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "active"]], target: "current",
        });
    }
    openCVExpiring() {
        const in30 = new Date(Date.now() + 30 * 86400000).toISOString().split("T")[0];
        this.action.doAction({
            type: "ir.actions.act_window", name: "CV expirant bientôt",
            res_model: "potting.confirmation.vente", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "active"], ["date_end", "<=", in30]], target: "current",
        });
    }
    createCV() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Nouvelle CV",
            res_model: "potting.confirmation.vente", view_mode: "form",
            views: [[false, "form"]], target: "current",
        });
    }

    // --- Formules ---
    openAllFormules() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Formules",
            res_model: "potting.formule", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["active", "=", true]], target: "current",
        });
    }
    openFormulesToPay() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Formules à payer",
            res_model: "potting.formule", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["active", "=", true], ["state", "=", "validated"]], target: "current",
        });
    }
    createFormule() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Nouvelle Formule",
            res_model: "potting.formule", view_mode: "form",
            views: [[false, "form"]], target: "current",
        });
    }

    // --- BL ---
    openDeliveryNotes() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Bons de livraison",
            res_model: "potting.delivery.note", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]], target: "current",
        });
    }
    openDeliveryNotesByState(state) {
        this.action.doAction({
            type: "ir.actions.act_window", name: `BL - ${state}`,
            res_model: "potting.delivery.note", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", state]], target: "current",
        });
    }
    createDeliveryNote() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Créer BL",
            res_model: "potting.quick.delivery.wizard", view_mode: "form",
            views: [[false, "form"]], target: "new",
        });
    }

    // --- Factures ---
    openInvoicesToValidate() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Factures à valider",
            res_model: "potting.forwarding.agent.invoice", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "submitted"]], target: "current",
        });
    }
    openInvoicesReady() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Factures prêtes au paiement",
            res_model: "potting.forwarding.agent.invoice", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "validated"]], target: "current",
        });
    }
    openAllInvoices() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Factures Transitaires",
            res_model: "potting.forwarding.agent.invoice", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]], target: "current",
        });
    }
    openInvoicesByState(state) {
        this.action.doAction({
            type: "ir.actions.act_window", name: `Factures - ${state}`,
            res_model: "potting.forwarding.agent.invoice", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", state]], target: "current",
        });
    }
    openPayments() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Paiements Transitaires",
            res_model: "potting.forwarding.agent.payment", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]], target: "current",
        });
    }

    // --- Production ---
    addQuickProduction() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Production rapide",
            res_model: "potting.quick.production.wizard", view_mode: "form",
            views: [[false, "form"]], target: "new",
        });
    }

    // --- Rapports ---
    openDailyReport() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Rapport quotidien",
            res_model: "potting.daily.report.wizard", view_mode: "form",
            views: [[false, "form"]], target: "new",
        });
    }
    openSendReport() {
        this.action.doAction({
            type: "ir.actions.act_window", name: "Envoyer par email",
            res_model: "potting.send.report.wizard", view_mode: "form",
            views: [[false, "form"]], target: "new",
        });
    }

    // --- Produit filtré ---
    openOTByProduct(product_type) {
        const cd = this.state.campaign ? [["campaign_id", "=", this.state.campaign.id]] : [];
        this.action.doAction({
            type: "ir.actions.act_window", name: `OT - ${product_type}`,
            res_model: "potting.transit.order", view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: [...cd, ["product_type", "=", product_type], ["state", "not in", ["cancelled"]]],
            target: "current",
        });
    }
}

registry.category("actions").add("potting_main_dashboard", PottingMainDashboard);
