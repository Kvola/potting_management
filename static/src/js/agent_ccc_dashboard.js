/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

/**
 * Dashboard pour le profil Agent CCC
 * Focus sur la création et gestion des Confirmations de Vente (CV)
 */
export class PottingAgentCCCDashboard extends Component {
    static template = "potting_management.AgentCCCDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            // Campagne active
            currentCampaign: null,
            
            // Statistiques CV
            cvStats: {
                total: 0,
                draft: 0,
                active: 0,
                expired: 0,
                consumed: 0,
                tonnage_autorise: 0,
                tonnage_utilise: 0,
                tonnage_disponible: 0,
                expiring_soon: 0,
            },
            
            // CV récentes
            recentCVs: [],
            
            // CV expirant bientôt (30 jours)
            expiringCVs: [],
            
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
                ["name", "code", "date_start", "date_end"],
                { limit: 1 }
            );
            if (campaigns.length > 0) {
                this.state.currentCampaign = campaigns[0];
            }
        } catch (e) {
            console.log("Campaign model not available");
        }

        await this.loadCVStats();
        await this.loadRecentData();
        await this.loadExpiringCVs();
        await this.loadProductStats();
    }

    async loadCVStats() {
        try {
            // Total des CV
            this.state.cvStats.total = await this.orm.searchCount(
                "potting.confirmation.vente", []
            );

            // CV par état
            const states = ['draft', 'active', 'expired', 'consumed'];
            for (const state of states) {
                this.state.cvStats[state] = await this.orm.searchCount(
                    "potting.confirmation.vente",
                    [['state', '=', state]]
                );
            }

            // Tonnages CV actives
            const cvData = await this.orm.searchRead(
                "potting.confirmation.vente",
                [['state', 'in', ['draft', 'active']]],
                ["tonnage_autorise", "tonnage_utilise", "tonnage_disponible"]
            );
            
            this.state.cvStats.tonnage_autorise = cvData.reduce(
                (sum, cv) => sum + (cv.tonnage_autorise || 0), 0
            );
            this.state.cvStats.tonnage_utilise = cvData.reduce(
                (sum, cv) => sum + (cv.tonnage_utilise || 0), 0
            );
            this.state.cvStats.tonnage_disponible = cvData.reduce(
                (sum, cv) => sum + (cv.tonnage_disponible || 0), 0
            );
        } catch (e) {
            console.error("Error loading CV stats:", e);
        }
    }

    async loadRecentData() {
        try {
            // CV récentes
            this.state.recentCVs = await this.orm.searchRead(
                "potting.confirmation.vente",
                [],
                ["name", "reference", "exportateur_id", "product_type", "tonnage_autorise", 
                 "tonnage_disponible", "date_validite", "state", "create_date"],
                { limit: 10, order: "create_date desc" }
            );
        } catch (e) {
            console.error("Error loading recent data:", e);
        }
    }

    async loadExpiringCVs() {
        try {
            // CV expirant dans les 30 prochains jours
            const today = new Date();
            const thirtyDaysLater = new Date();
            thirtyDaysLater.setDate(today.getDate() + 30);
            
            const todayStr = today.toISOString().split('T')[0];
            const futureStr = thirtyDaysLater.toISOString().split('T')[0];

            this.state.expiringCVs = await this.orm.searchRead(
                "potting.confirmation.vente",
                [
                    ['state', '=', 'active'],
                    ['date_validite', '>=', todayStr],
                    ['date_validite', '<=', futureStr]
                ],
                ["name", "reference", "exportateur_id", "tonnage_disponible", "date_validite"],
                { limit: 10, order: "date_validite asc" }
            );

            this.state.cvStats.expiring_soon = this.state.expiringCVs.length;
        } catch (e) {
            console.error("Error loading expiring CVs:", e);
        }
    }

    async loadProductStats() {
        try {
            const cvs = await this.orm.searchRead(
                "potting.confirmation.vente",
                [['state', 'in', ['draft', 'active']]],
                ["product_type", "tonnage_autorise", "tonnage_disponible"]
            );

            const productMap = {};
            for (const cv of cvs) {
                const ptype = cv.product_type || 'unknown';
                if (!productMap[ptype]) {
                    productMap[ptype] = { type: ptype, count: 0, tonnage_autorise: 0, tonnage_disponible: 0 };
                }
                productMap[ptype].count++;
                productMap[ptype].tonnage_autorise += cv.tonnage_autorise || 0;
                productMap[ptype].tonnage_disponible += cv.tonnage_disponible || 0;
            }

            this.state.productStats = Object.values(productMap).sort(
                (a, b) => b.tonnage_autorise - a.tonnage_autorise
            );
        } catch (e) {
            console.error("Error loading product stats:", e);
        }
    }

    // ============ Actions ============

    createCV() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Nouvelle Confirmation de Vente',
            res_model: 'potting.confirmation.vente',
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openCVs(state = null) {
        const domain = state ? [['state', '=', state]] : [];
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Confirmations de Vente',
            res_model: 'potting.confirmation.vente',
            views: [[false, 'list'], [false, 'kanban'], [false, 'form']],
            domain: domain,
            context: {},
        });
    }

    openExpiringCVs() {
        const today = new Date();
        const thirtyDaysLater = new Date();
        thirtyDaysLater.setDate(today.getDate() + 30);
        
        const todayStr = today.toISOString().split('T')[0];
        const futureStr = thirtyDaysLater.toISOString().split('T')[0];

        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'CV expirant bientôt',
            res_model: 'potting.confirmation.vente',
            views: [[false, 'list'], [false, 'form']],
            domain: [
                ['state', '=', 'active'],
                ['date_validite', '>=', todayStr],
                ['date_validite', '<=', futureStr]
            ],
            context: {},
        });
    }

    openCV(cvId) {
        this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: 'potting.confirmation.vente',
            res_id: cvId,
            views: [[false, 'form']],
            target: 'current',
        });
    }

    openTonnageTransferWizard() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Transfert de tonnage CV',
            res_model: 'potting.cv.tonnage.transfer.wizard',
            views: [[false, 'form']],
            target: 'new',
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

    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('fr-FR');
    }

    getDaysUntilExpiry(dateStr) {
        if (!dateStr) return null;
        const today = new Date();
        const expiry = new Date(dateStr);
        const diffTime = expiry - today;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        return diffDays;
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
            'active': 'Active',
            'expired': 'Expirée',
            'consumed': 'Consommée',
        };
        return labels[state] || state;
    }

    getStateBadgeClass(state) {
        const classes = {
            'draft': 'badge bg-secondary',
            'active': 'badge bg-success',
            'expired': 'badge bg-danger',
            'consumed': 'badge bg-info',
        };
        return classes[state] || 'badge bg-secondary';
    }

    getExpiryBadgeClass(daysUntil) {
        if (daysUntil === null) return 'badge bg-secondary';
        if (daysUntil <= 7) return 'badge bg-danger';
        if (daysUntil <= 15) return 'badge bg-warning';
        return 'badge bg-info';
    }
}

// Register the client action
registry.category("actions").add("potting_agent_ccc_dashboard", PottingAgentCCCDashboard);
