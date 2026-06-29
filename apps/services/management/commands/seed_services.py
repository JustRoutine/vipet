"""
Management command to seed the database with default VIPet services.
Run with: python manage.py seed_services
"""

from django.core.management.base import BaseCommand

from apps.services.models import Service


class Command(BaseCommand):
    help = "Seed the database with default VIPet premium services"

    def handle(self, *args, **options):
        services = [
            {
                "name": "Suite Royale",
                "category": "luxury_suite",
                "description": "Chambre privée et climatisée avec literie premium, surveillance 24h/24 et service de conciergerie personnalisé pour votre animal.",
                "price": 500,
            },
            {
                "name": "Suite Présidentielle",
                "category": "luxury_suite",
                "description": "Notre suite la plus exclusive avec espace privé, caméra live, lit king-size pour animaux et room service quotidien.",
                "price": 900,
            },
            {
                "name": "Toilettage VIP",
                "category": "grooming",
                "description": "Toilettage complet par nos experts : bain, coupe, brushing, soin des griffes et parfum signature VIPET.",
                "price": 200,
            },
            {
                "name": "Toilettage Express",
                "category": "grooming",
                "description": "Bain rapide, séchage et brossage pour un look frais en 30 minutes.",
                "price": 120,
            },
            {
                "name": "Soins Spa Premium",
                "category": "spa",
                "description": "Bain relaxant aux huiles essentielles, massage thérapeutique et soin hydratant pour pelage soyeux.",
                "price": 350,
            },
            {
                "name": "Spa Détente",
                "category": "spa",
                "description": "Bain moussant apaisant et massage doux pour réduire le stress de votre compagnon.",
                "price": 200,
            },
            {
                "name": "Garderie Journée",
                "category": "daycare",
                "description": "Journée complète de jeux supervisés, socialisation et activités stimulantes dans nos espaces sécurisés.",
                "price": 150,
            },
            {
                "name": "Garderie Demi-Journée",
                "category": "daycare",
                "description": "4 heures d'activités et de jeux en groupe avec surveillance professionnelle.",
                "price": 80,
            },
            {
                "name": "Éducation & Dressage",
                "category": "training",
                "description": "Sessions individuelles d'éducation canine avec nos dresseurs certifiés. Obéissance, socialisation et comportement.",
                "price": 300,
            },
            {
                "name": "Stage Obéissance (5 jours)",
                "category": "training",
                "description": "Programme intensif de 5 jours pour renforcer les commandes de base et améliorer le comportement.",
                "price": 1200,
            },
            {
                "name": "Consultation Vétérinaire",
                "category": "veterinary_checkup",
                "description": "Examen complet par notre vétérinaire sur place : auscultation, vaccins, analyses et suivi de santé.",
                "price": 250,
            },
            {
                "name": "Bilan de Santé Complet",
                "category": "veterinary_checkup",
                "description": "Check-up approfondi avec analyses sanguines, radiographie si nécessaire et rapport détaillé.",
                "price": 500,
            },
            {
                "name": "Fête d'Anniversaire",
                "category": "birthday_events",
                "description": "Célébration complète avec gâteau personnalisé, décorations thématiques, photos professionnelles et invités animaux.",
                "price": 800,
            },
            {
                "name": "Mini Fête",
                "category": "birthday_events",
                "description": "Petite célébration intime avec gâteau, chapeau festif et séance photo souvenir.",
                "price": 400,
            },
        ]

        created_count = 0
        for service_data in services:
            _, created = Service.objects.get_or_create(
                name=service_data["name"],
                defaults=service_data,
            )
            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Done! {created_count} services created, {len(services) - created_count} already existed.")
        )
